import random, textwrap
from typing import Iterable
from .parser import Parser, Token
from .collections import Choices, Reversed, Word
from .exceptions import RuleError, SoundChangeError

MAX_DEPTH = 10

class Language:
    def __init__(self, file = '', /):
        self.letters: dict[str, int] = {}
        self.variables: dict[str, Choices[str]] = {}
        self.rules: dict[str, Choices[Word]] = {}
        self.changes: list[SoundChange] = []
        self.segments: set[str] = set()
        self.longest_segment = 1
        self._start_rule = ''
        if file: self.open(file)

    def generate(self, count = 1, /, *, sorted = False):
        if not self.rules:
            raise RuleError('no rules defined')
        words = self.apply(self._run_rule(self.start_rule) for _ in range(count))
        return self.sorted(words) if sorted else list(words)

    def textify(self, sentences = 11, width = 70):
        def sentence():
            words = [str(word) for word in self.generate(random.randint(4, 12))]
            if len(words) > 6:
                words[random.randint(1, len(words) - 1)] += ','
            words[-1] += random.choices('.?!', [8, 1, 1])[0]
            return ' '.join(words).capitalize()
        text = ' '.join(sentence() for _ in range(sentences))
        return textwrap.fill(text, width)

    def apply(self, words: Iterable[Word], /):
        for word in words:
            for change in self.changes:
                word = change.apply(word)
            yield word

    def sorted(self, words: Iterable[Word], /, *, reverse = False):
        key = lambda word: [self.letters.get(l, -1) for l in word]
        return sorted(words, key=key, reverse=reverse)

    def normalize(self, text: str, /):
        return Word(str(t) for t in Token(text.strip()).normalize(self))

    def open(self, file: str, /):
        Parser.open(file).parse(self)

    def parse(self, text: str, /):
        Parser(text).parse(self)

    def update_letters(self, letters: Iterable[str], /):
        self.letters.clear()
        for i, l in enumerate(letters):
            self._cache_segment(l)
            self.letters[l] = i

    def set_variable(self, name: str, variable: Choices[str], /):
        self._cache_segment(name)
        for letter in variable:
            self._cache_segment(letter)
        self.variables[name] = variable

    def set_rule(self, name: str, rule: Choices[Word], /):
        self._start_rule = ''
        if name != 'word':
            self._cache_segment(name)
        self.rules[name] = rule

    def _cache_segment(self, segment: str, /):
        length = len(segment)
        if length <= 1:
            return
        self.segments.add(segment)
        if length > self.longest_segment:
            self.longest_segment = length

    @property
    def start_rule(self):
        if not self._start_rule:
            self._start_rule = 'word' if 'word' in self.rules else list(self.rules)[-1]
        return self._start_rule

    def _run_rule(self, name: str, depth = 0) -> Word:
        word = Word()
        if depth > MAX_DEPTH:
            raise RuleError(f"rule '{name}' exceeded maximum recursion depth")
        for expr in self.rules[name].choose():
            if var := self.variables.get(expr):
                word.append(var.choose())
            elif expr in self.rules:
                word += self._run_rule(expr, depth + 1)
            else:
                word.append(expr)
        return word

class SoundChange:
    def __init__(self, language: Language):
        self.language = language
        self.sources: list[Pattern] = []
        self.targets: list[Pattern] = []
        self.before = Pattern()
        self.after = Pattern()

    def apply(self, word: Word, /):
        if not self.sources:
            return self._insert(word)
        for i in range(len(self.sources)):
            word = self._transform(i, word)
        return word

    def _insert(self, word: Word):
        result, match = Word(), Match()
        for i in range(len(word) + 1):
            if self._env(word, i, match):
                result += self.targets[0].build_target(match, self.language)
            if i < len(word):
                result.append(word[i])
        return result

    def _transform(self, index: int, word: Word):
        result = Word()
        i = 0
        while i < len(word):
            match = self.sources[index].match_source(word[i:], self.language)
            if match and self._env(word, i, match):
                result += self.targets[index].build_target(match, self.language)
                i += len(match.letters)
            else:
                result.append(word[i])
                i += 1
        return result

    def _env(self, word: Word, at: int, match: 'Match'):
        if self.before and not self.before.match_env(word[:at], match, self.language, reversed=True):
            return False
        if self.after and not self.after.match_env(word[at + len(match.letters):], match, self.language):
            return False
        return True

class Pattern(list[str]):
    def match_source(self, letters: list[str], /, lang: Language):
        if len(self) > len(letters):
            return None
        match = Match()
        for i in range(len(self)):
            left, right = self[i], letters[i]
            if var := lang.variables.get(left):
                try:
                    index = var.index(right)
                    match.append(right, index)
                except ValueError:
                    return None
            elif left == right:
                match.append(right)
            else:
                return None
        return match

    def match_env(self, letters: list[str], /, match: 'Match', lang: Language, *, reversed = False):
        env: list[str] = []
        for seg in self:
            if seg == '@' or seg == '$0':
                env += match.letters
            elif seg[0] == '$':
                env.append(self._backref(seg, match))
            else:
                env.append(seg)
        if reversed:
            letters = Reversed(letters)
            env = Reversed(env)
        for i, left in enumerate(env):
            if i == len(letters):
                return left == '#'
            right = letters[i]
            if var := lang.variables.get(left):
                if right not in var:
                    return False
                elif left != right:
                    return False
        return True

    def build_target(self, match: 'Match', lang: Language):
        result: list[str] = []
        for i, seg in enumerate(self):
            if seg == '@' or seg == '$0':
                result += match.letters
            elif seg[0] == '$':
                result.append(self._backref(seg, match))
            elif var := lang.variables.get(seg):
                if i >= len(var):
                    raise SoundChangeError(f"sound change: variable '{seg}' in target out of bounds of source")
                index = match.indexes[i]
                if index < 0:
                    raise SoundChangeError(f"sound change: no matching variable in source for '{seg}' in target")
                if index > len(var):
                    raise SoundChangeError(f"sound change: variable '{seg}' in target out of bounds of matching variable in source")
                result.append(var[index])
            else:
                result.append(seg)
        return result

    def _backref(self, letter: str, match: 'Match'):
        try:
            j = int(letter[1]) - 1
            return match.letters[j]
        except IndexError:
            raise SoundChangeError(f"sound change: backref '{letter}' out of bounds of source")
        except ValueError:
            raise SoundChangeError(f"sound change: backref '{letter}' index not a number")

class Match:
    def __init__(self):
        self.letters: list[str] = []
        self.indexes: list[int] = []

    def append(self, letter: str, index = -1, /):
        self.letters.append(letter)
        self.indexes.append(index)
