import math, random, textwrap
from typing import Iterable
from .segment import Segment
from .exceptions import ParseError, RuleError, SoundChangeError
from .utils import reverse

class Word(list[str]):
    def __repr__(self):
        return f'Word({super().__repr__()})'

    def __str__(self):
        return ''.join(self)

class Language:
    MAX_DEPTH = 10

    def __init__(self):
        self.letters = dict[str, int]()
        self.classes = dict[str, Choices[str]]()
        self.rules = dict[str, Choices[Word]]()
        self.changes = list[SoundChange]()
        self.longest_segment = 1
        self.start_rule = ''

    def apply(self, words: Iterable[Word]):
        def inner(word: Word):
            for change in self.changes:
                word = change.apply(word)
            return word
        return map(inner, words)

    def generate(self, count = 1, *, sorted = False):
        if not self.rules:
            raise RuleError('no rules defined')
        if not self.start_rule:
            self.start_rule = 'word' if 'word' in self.rules else list(self.rules)[-1]
        words = self.apply(self.run_rule(self.start_rule) for _ in range(count))
        return self.sort(words) if sorted else list(words)

    def normalize(self, segment: str | Segment):
        if isinstance(segment, str):
            segment = Segment(segment)
        result = list[Segment]()
        i = 0
        while i < len(segment):
            match segment[i]:
                case '$':
                    result.append(segment[i:i + 2])
                    i += 2
                case '[':
                    try:
                        j = segment.string.index(']', i) + 1
                        result.append(segment[i:i + j])
                        i += j
                    except ValueError:
                        raise ParseError("unmatched '['", segment[i])
                case ']':
                    raise ParseError("unmatched ']'", segment[i])
                case _:
                    for j in range(self.longest_segment, 0, -1):
                        seg = segment[i:i + j]
                        if j == 1 or str(seg) in self.classes or str(seg) in self.rules:
                            result.append(seg)
                            i += j
                            break
        return result

    def normalizew(self, segment: str | Segment):
        return Word(map(str, self.normalize(segment)))

    def order_letters(self, letters: Iterable[str]):
        self.letters = {l: i for i, l in enumerate(letters)}

    def run_rule(self, name: str, depth = 0) -> Word:
        if depth > Language.MAX_DEPTH:
            raise RuleError('maximum recursion depth exceeded')
        if name not in self.rules:
            raise RuleError(f"rule '{name}' not defined")
        result = Word()
        for r in self.rules[name].choose():
            if r in self.classes:
                result.append(self.classes[r].choose())
            elif r in self.rules:
                result += self.run_rule(r, depth + 1)
            else:
                result.append(r)
        return result

    def sort(self, words: Iterable[Word], *, reverse = False):
        def key(word: Word):
            return [self.letters.get(l, -1) for l in word]
        return sorted(words, key=key, reverse=reverse)

    def textify(self, sentences = 11, width = 70):
        def sentence():
            words = list(map(str, self.generate(random.randint(4, 12))))
            if len(words) > 6:
                words[random.randint(1, len(words) - 2)] += ','
            words[-1] += random.choices('.?!', [8, 1, 1])[0]
            return ' '.join(words).capitalize()
        text = ' '.join(sentence() for _ in range(sentences))
        return textwrap.fill(text, width)

    def update_longest(self, string: str | Segment):
        if string[0] != '[' and len(string) > self.longest_segment:
            self.longest_segment = len(string)

    def open(self, file: str, **kwargs):
        for line in Segment.open(file, **kwargs):
            self.parse(line)
        return self

    def parse(self, segment: str | Segment):
        if isinstance(segment, str):
            segment = Segment(segment)
        lexed = segment.lex()
        if not lexed:
            pass
        elif lexed[0] == 'letters':
            self._parse_letters(lexed)
        elif '=' in lexed:
            self._parse_class(lexed)
        elif '::' in lexed:
            self._parse_rule(lexed)
        elif '>' in lexed:
            self.changes.append(SoundChange(self)._parse(lexed))
        else:
            raise ParseError('invalid keyword', lexed[0])

    def _parse_letters(self, lexed: list[Segment]):
        lexed = self.normalize(lexed[1]) if len(lexed) == 2 else lexed[1:]
        self.order_letters(map(str, lexed))

    def _parse_class(self, lexed: list[Segment]):
        head, tail = Segment.partition(lexed, '=')
        if len(head) != 1 or not tail:
            raise ParseError('invalid class', lexed[0], highlight=False)
        if len(tail) == 1:
            tail = self.normalize(tail[0])
        class_ = Choices[str]()
        for letter in tail:
            self.update_longest(letter)
            class_.append(str(letter))
        class_.natural_weights()
        self.update_longest(head[0])
        self.classes[str(head[0])] = class_

    def _parse_rule(self, lexed: list[Segment]):
        head, tail = Segment.partition(lexed, '::')
        if len(head) != 1 or not tail:
            raise ParseError('invalid rule', lexed[0], highlight=False)
        rule = Choices[Word]()
        for expr in tail:
            rule.append(self.normalizew(expr))
        rule.natural_weights()
        self.update_longest(head[0])
        self.rules[str(head[0])] = rule

class Choices[T]:
    def __init__(self):
        self.values = list[T]()
        self.weights = list[float]()

    def __len__(self):
        return len(self.values)

    def __contains__(self, key: T, /):
        return key in self.values

    def __getitem__(self, key: int, /):
        return self.values[key]

    def append(self, value: T, weight = 1.):
        self.values.append(value)
        self.weights.append(weight)

    def choose(self):
        return random.choices(self.values, self.weights)[0]

    def index(self, value: T, /):
        return self.values.index(value)

    def natural_weights(self):
        n = len(self)
        for i in range(n):
            self.weights[i] = (math.log(n + 1) - math.log(i + 1)) / n

class Match:
    def __init__(self, source: list[Segment]):
        self.source = source
        self.letters = list[str]()
        self.indexes = list[int]()

    def append(self, letter: str, index = -1):
        self.letters.append(letter)
        self.indexes.append(index)

class Pattern(list[Segment]):
    def match_source(self, word: list[str], lang: Language):
        if len(self) > len(word):
            return None
        match = Match(self)
        for i in range(len(self)):
            left, right = self[i], word[i]
            if left == '@' or left == '#':
                raise SoundChangeError(f"'{left}' in source", left)
            elif left[0] == '$':
                raise SoundChangeError('backref in source', left)
            elif str(left) in lang.classes:
                try:
                    index = lang.classes[str(left)].index(right)
                    match.append(right, index)
                except ValueError:
                    return None
            elif left == right:
                match.append(right)
            else:
                return None
        return match

    def match_env(self, word: list[str], match: Match, lang: Language, *, reversed = False):
        env = list[str | Segment]()
        for seg in self:
            if seg == '@':
                env += match.letters
            elif seg[0] == '$':
                env.append(self.backref(seg, match))
            else:
                env.append(seg)
        if reversed:
            env = reverse(env)
            word = reverse(word)
        for i, left in enumerate(env):
            if i == len(word):
                return left == '#'
            right = word[i]
            if str(left) in lang.classes:
                if right not in lang.classes[str(left)]:
                    return False
            elif left != right:
                return False
        return True

    def build_target(self, match: Match, lang: Language):
        result = Word()
        for i, seg in enumerate(self):
            if seg == '@':
                result += match.letters
            elif seg == '#':
                raise SoundChangeError("'#' in target", seg)
            elif seg[0] == '$':
                result.append(self.backref(seg, match))
            elif str(seg) in lang.classes:
                if i >= len(match.source):
                    raise SoundChangeError('class in target out of bounds', seg)
                source, index = match.source[i], match.indexes[i]
                if index < 0:
                    raise SoundChangeError('no class in source for class in target', source, seg)
                scls, tcls = lang.classes[str(source)], lang.classes[str(seg)]
                if len(scls) != len(tcls):
                    raise SoundChangeError('classes different length', source, seg)
                result.append(tcls[index])
            else:
                result.append(str(seg))
        return result

    def backref(self, segment: Segment, match: Match):
        try:
            j = int(str(segment[1])) - 1
            return match.letters[j]
        except IndexError:
            raise SoundChangeError('backref out of bounds', segment)
        except ValueError:
            raise SoundChangeError('invalid backref', segment)

class SoundChange:
    def __init__(self, lang: Language):
        self.lang = lang
        self.sources = list[Pattern]()
        self.targets = list[Pattern]()
        self.before = Pattern()
        self.after = Pattern()

    def apply(self, word: Word):
        if not self.sources:
            return self.insert(word)
        for i in range(len(self.sources)):
            word = self.transform(self.sources[i], self.targets[i], word)
        return word

    def insert(self, word: Word):
        result = Word()
        match = Match([])
        for i in range(len(word) + 1):
            if self._env(word[:i], word[i:], match):
                result += self.targets[0].build_target(match, self.lang)
            if i < len(word):
                result.append(word[i])
        return result

    def transform(self, source: Pattern, target: Pattern, word: Word):
        result = Word()
        i = 0
        while i < len(word):
            match = source.match_source(word[i:], self.lang)
            if match and self._env(word[:i], word[i + len(match.letters):], match):
                result += target.build_target(match, self.lang)
                i += len(match.letters)
            else:
                result.append(word[i])
                i += 1
        return result

    def _env(self, before: list[str], after: list[str], match: Match):
        if self.before and not self.before.match_env(before, match, self.lang, reversed=True):
            return False
        if self.after and not self.after.match_env(after, match, self.lang):
            return False
        return True

    def _parse(self, lexed: list[Segment]):
        sources, targets, before, after = Segment.partition(lexed, '>', '/', '_')
        if not sources and not targets:
            raise ParseError('no sources or targets', lexed[0], highlight=False)
        if not sources and len(targets) > 1:
            raise ParseError('too many targets in insertion', *targets)
        if len(targets) > 1 and len(sources) != len(targets):
            raise ParseError('sources and targets different length', *sources, *targets)
        if len(before) > 1 or len(after) > 1:
            raise ParseError('invalid environment', *before, *after)
        spats = [Pattern(self.lang.normalize(seg)) for seg in sources]
        tpats = [Pattern(self.lang.normalize(seg)) for seg in targets]
        if spats and not tpats:
            tpats = [Pattern()]
        if len(spats) > 1 and len(tpats) == 1:
            tpats *= len(spats)
        self.sources = spats
        self.targets = tpats
        if before:
            self.before = Pattern(self.lang.normalize(before[0]))
        if after:
            self.after = Pattern(self.lang.normalize(after[0]))
        return self
