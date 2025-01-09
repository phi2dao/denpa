import random, textwrap
from typing import Iterable
from .parser import Parser, Token
from .collections import Choices, Word
from .exceptions import RuleError

MAX_DEPTH = 10

class Language:
    def __init__(self, file = '', /):
        self.letters: dict[str, int] = {}
        self.variables: dict[str, Choices[str]] = {}
        self.rules: dict[str, Choices[Word]] = {}
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
