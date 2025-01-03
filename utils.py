class record:
    __match_args__ = ()

    @property
    def __attrs(self):
        return tuple(getattr(self, attr) for attr in self.__class__.__match_args__)

    def __eq__(self, other: object, /):
        if isinstance(other, self.__class__):
            return self.__attrs == other.__attrs
        return super().__eq__(other)

    def __hash__(self):
        return hash(self.__attrs)

    def __repr__(self):
        return f'{self.__class__.__name__}({', '.join(repr(x) for x in self.__attrs)})'

class reverse[T](list[T]):
    def __getitem__(self, key: int, /):
        if key >= len(self):
            raise IndexError('list index out of range')
        return super().__getitem__(len(self) - key - 1)

    def __repr__(self):
        return f'reverse({super().__repr__()})'

def fill[T](list_: list[T], to: int, value: T):
    list_ += [value] * (to - len(list_))
