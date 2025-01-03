import math, random, textwrap
from .segment import Segment
from .exceptions import ParseError, RuleError

MAX_DEPTH = 10

class Word(list[str]):
    def __repr__(self):
        return f'Word({super().__repr__()})'

    def __str__(self):
        return ''.join(self)

class Language:
    def __init__(self):
        self.letters = dict[str, int]()
        self.classes = dict[str, Choices[str]]()
        self.rules = dict[str, Choices[Word]]()
        self.longest_segment = 1
        self.start_rule = ''

    def generate(self, n = 1, *, sorted = False):
        if not self.rules:
            raise RuleError('no rules defined')
        if not self.start_rule:
            self.start_rule = 'word' if 'word' in self.rules else list(self.rules)[-1]
        words = [self.run_rule(self.start_rule) for _ in range(n)]
        return self.sort(words) if sorted else words

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
        return Word(str(seg) for seg in self.normalize(segment))

    def order_letters(self, letters: list[str]):
        self.letters = {l: i for i, l in enumerate(letters)}

    def run_rule(self, name: str, depth = 0) -> Word:
        if depth > MAX_DEPTH:
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

    def sort(self, words: list[Word], *, reverse = False):
        key = lambda word: [self.letters[l] for l in word]
        return sorted(words, key=key, reverse=reverse)

    def textify(self, sentences = 11, width = 70):
        def sentence():
            words = [str(word) for word in self.generate(random.randint(4, 12))]
            if len(words) > 6:
                words[random.randint(1, len(words) - 2)] += ','
            words[-1] += random.choices('.?!', [8, 1, 1])[0]
            return ' '.join(words).capitalize()
        text = ' '.join(sentence() for _ in range(sentences))
        return textwrap.fill(text, width)

    def update_longest(self, string: str):
        if string[0] != '[' and len(string) > self.longest_segment:
            self.longest_segment = len(string)

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
