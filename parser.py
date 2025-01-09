import dataclasses, re
from pathlib import Path
from .collections import Choices, Word
from .exceptions import ParseError, ImportError

from typing import TYPE_CHECKING
if TYPE_CHECKING: from .language import Language, SoundChange

OP = re.compile(r'=|::|>|/|_')
WHITESPACE = re.compile(r'\s+')
COMMENT = re.compile(r'%.*$')

class Parser:
    @staticmethod
    def open(file: str, /):
        with open(file, 'r', encoding='utf-8') as f:
            return Parser(f.read(), file)

    def __init__(self, text: str, /, file = ''):
        self.lines = [line.strip().expandtabs() for line in text.splitlines()]
        self.tokens = [Token(line, i, 0) for i, line in enumerate(self.lines)]
        self.file = file

    def parse(self, lang: 'Language', /):
        for line in self.tokens:
            lexed = line.lex()
            if not lexed:
                pass
            elif lexed[0] == 'import':
                self._parse_import(lexed, lang)
            elif lexed[0] == 'letters':
                self._parse_letters(lexed, lang)
            elif '=' in lexed:
                self._parse_variable(lexed, lang)
            elif '::' in lexed:
                self._parse_rule(lexed, lang)
            elif '>' in lexed:
                self._parse_sound_change(lexed, lang)
            else:
                raise ParseError(f"statement: unknown keyword '{lexed[0]}'", self, lexed[0])

    def _parse_import(self, line: list['Token'], lang: 'Language'):
        if len(line) < 2:
            raise ImportError('no files to import', self, line[0])
        for file in line[1:]:
            try:
                path = Path(self.file).parent / str(file)
                Parser.open(str(path)).parse(lang)
            except (FileNotFoundError, ParseError) as e:
                raise ImportError(f"cannot import '{file}'", self, file) from e

    def _parse_letters(self, line: list['Token'], lang: 'Language'):
        if len(line) < 2:
            raise ParseError("statement: no letters after 'letters'", self, line[0])
        letters = line[1].normalize(lang) if len(line) == 2 else line[1:]
        lang.update_letters(str(l) for l in letters)

    def _parse_variable(self, line: list['Token'], lang: 'Language'):
        head, op, tail = Token.partition(line, '=')
        if len(head) != 1:
            raise ParseError(f'variable: {len(head)} names, should be 1', self, op[0])
        head = head[0].text
        if not tail:
            raise ParseError('variable: no letters in variable', self, op[0])
        if len(tail) == 1:
            tail = tail[0].normalize(lang)
        var, natural = Choices[str](), True
        for token in tail:
            letter, weight = self._parse_weight(token)
            var.append(letter, weight)
            natural = natural and weight == 1.
        if natural:
            var.natural_weights()
        lang.set_variable(head, var)

    def _parse_rule(self, line: list['Token'], lang: 'Language'):
        head, op, tail = Token.partition(line, '::')
        if len(head) != 1:
            raise ParseError(f'rule: {len(head)} names, should be 1', self, op[0])
        head = head[0].text
        if not tail:
            raise ParseError('rule: no expressions in rule', self, op[0])
        rule, natural = Choices[Word](), True
        for token in tail:
            pattern, weight = self._parse_weight(token)
            rule.append(lang.normalize(pattern), weight)
            natural = natural and weight == 1.
        if natural:
            rule.natural_weights()
        lang.set_rule(head, rule)

    def _parse_weight(self, token: 'Token'):
        if '#' in token.text:
            parts = token.text.split('#')
            if len(parts) != 2:
                raise ParseError(f'weight: {len(parts)} part(s), should be 2', self, token)
            try:
                return parts[0], float(parts[1])
            except ValueError:
                raise ParseError(f"weight: '{parts[1]}' is not a number", self, token)
        return token.text, 1.

    def _parse_sound_change(self, line: list['Token'], lang: 'Language'):
        from .language import SoundChange
        sources, trans, targets, env, before, under, after = Token.partition(line, '>', '/', '_')
        change = SoundChange(lang)
        self._parse_transform(sources, trans[0], targets, change)
        self._parse_environment(before, env + under, after, change)
        lang.changes.append(change)

    def _parse_transform(self, sources: list['Token'], op: 'Token', targets: list['Token'], change: 'SoundChange'):
        from .language import Pattern
        lens, lent = len(sources), len(targets)
        if not lens and not lent:
            raise ParseError('sound change: empty transform', self, op)
        if not lens and lent > 1:
            raise ParseError('sound change: multiple targets in insertion', self, targets[1])
        if lent > 1 and lens != lent:
            raise ParseError('sound change: sources and targets different length', self, op)
        pats = [self._parse_transform_source(s, change) for s in sources]
        patt = [self._parse_transform_target(t, change) for t in targets]
        if pats and not patt:
            patt.append(Pattern())
        if pats and len(patt) == 1:
            patt *= len(pats)
        change.sources, change.targets = pats, patt

    def _parse_transform_source(self, source: 'Token', change: 'SoundChange'):
        tokens = source.normalize(change.language)
        for token in tokens:
            if token.text[0] in '@#$':
                raise ParseError(f"sound change: '{token.text[0]}' in source", self, token)
        return Token.pattern(tokens)

    def _parse_transform_target(self, target: 'Token', change: 'SoundChange'):
        tokens = target.normalize(change.language)
        for token in tokens:
            if token.text == '#':
                raise ParseError("sound change: '#' in target", self, token)
        return Token.pattern(tokens)

    def _parse_environment(self, before: list['Token'], ops: list['Token'], after: list['Token'], change: 'SoundChange'):
        lenb, leno, lena = len(before), len(ops), len(after)
        if leno == 0 or lenb == 0:
            return
        if leno == 1 and lenb > 0:
            raise ParseError("sound change: environment missing '_'", self, before[0])
        if lenb > 1:
            raise ParseError("sound change: environment: too many patterns before '_'", self, before[1])
        if lena > 1:
            raise ParseError("sound change: environment: too many patterns after '_'", self, after[1])
        if before:
            change.before = Token.pattern(before[0].normalize(change.language))
        if after:
            change.after = Token.pattern(after[0].normalize(change.language))

@dataclasses.dataclass
class Token:
    text: str
    ln: int = 0
    col: int = 0

    @staticmethod
    def index(tokens: list['Token'], value: str, /):
        for i, token in enumerate(tokens):
            if token.text == value:
                return i
        raise ValueError(f"'{value}' is not in list")

    @staticmethod
    def partition(tokens: list['Token'], *seps: str):
        result: list[list[Token]] = []
        for sep in seps:
            try:
                j = Token.index(tokens, sep)
                result.append(tokens[:j])
                result.append([tokens[j]])
                tokens = tokens[j + 1:]
            except ValueError:
                break
        result.append(tokens)
        while len(result) < (len(seps) * 2 + 1):
            result.append([])
        return result

    @staticmethod
    def pattern(tokens: list['Token'], /):
        from .language import Pattern
        return Pattern(str(t) for t in tokens)

    def __len__(self):
        return len(self.text)

    def __getitem__(self, key: int | slice, /):
        text = self.text[key]
        start = (key.start or 0) if isinstance(key, slice) else key
        return Token(text, self.ln, self.col + start)

    def lex(self):
        result: list[Token] = []
        start, i = -1, 0
        def append():
            nonlocal start
            if start >= 0:
                result.append(self[start:i])
                start = -1
        while i < len(self.text):
            if match := OP.match(self.text, i):
                append()
                n = len(match.group())
                result.append(self[i:i + n])
                i += n
            elif match := WHITESPACE.match(self.text, i):
                append()
                i += len(match.group())
            elif match := COMMENT.match(self.text, i):
                append()
                return result
            elif start < 0:
                start = i
                i += 1
            else:
                i += 1
        append()
        return result

    def normalize(self, lang: 'Language', /):
        result: list[Token] = []
        i = 0
        while i < len(self):
            if self.text[i] == '$':
                result.append(self[i:i + 2])
                i += 2
                continue
            for j in range(lang.longest_segment, 0, -1):
                seg = self[i:i + j]
                if j == 1 or seg.text in lang.segments:
                    result.append(seg)
                    i += j
                    break
        return result

    def __eq__(self, other: object, /):
        return str(self) == str(other)

    def __str__(self):
        return self.text
