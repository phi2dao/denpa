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

def fill[T](list_: list[T], to: int, value: T):
    list_ += [value] * (to - len(list_))
