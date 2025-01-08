import math, random
from typing import Iterable

class Choices[T]:
    def __init__(self, source: Iterable[T] = [], /):
        self.values = list(source)
        self.weights = [1.] * len(self.values)

    def __len__(self):
        return len(self.values)

    def __contains__(self, key: object, /):
        return key in self.values

    def __getitem__(self, key: int, /):
        return self.values[key]

    def __delitem__(self, key: int, /):
        del self.values[key]
        del self.weights[key]

    def choose(self):
        return random.choices(self.values, self.weights)[0]

    def append(self, value: T, weight = 1., /):
        self.values.append(value)
        self.weights.append(weight)

    def set(self, value: T, weight: float, /):
        try:
            self.weights[self.index(value)] = weight
        except ValueError:
            self.append(value, weight)

    def remove(self, value: T, /):
        try:
            del self[self.index(value)]
        except ValueError:
            pass

    def index(self, value: T, /):
        return self.values.index(value)

    def natural_weights(self):
        n = len(self)
        for i in range(n):
            self.weights[i] = (math.log(n + 1) - math.log(i + 1)) / n

class Reversed[T](list[T]):
    def __getitem__(self, key: int, /):
        if key >= len(self):
            raise IndexError('list index out of range')
        return super().__getitem__(len(self) - key - 1)

class Word(list[str]):
    def __repr__(self):
        return f'Word({super().__repr__()})'

    def __str__(self):
        return ''.join(self)
