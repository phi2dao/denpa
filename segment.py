from .utils import record, fill

class Segment(record):
    __match_args__ = ('string', 'ln', 'col', 'file')

    @staticmethod
    def index(segments: list['Segment'], value: str, /):
        for i, seg in enumerate(segments):
            if seg == value:
                return i
        raise ValueError(f"'{value}' is not in list")

    @staticmethod
    def open(file: str, **kwargs):
        with open(file, 'r', encoding='utf-8', **kwargs) as f:
            result = [Segment(line.strip(), i, 0, file) for i, line in enumerate(f)]
        return result

    @staticmethod
    def partition(segments: list['Segment'], *seps: str):
        result = list[list[Segment]]()
        for sep in seps:
            try:
                j = Segment.index(segments, sep)
                result.append(segments[:j])
                segments = segments[j + 1:]
            except ValueError:
                break
        result.append(segments)
        fill(result, len(seps) + 1, [])
        return result

    def __init__(self, string: str, ln = 0, col = 0, file = '__main__', *, cache = True):
        self.string = string
        self.ln = ln
        self.col = col
        self.file = file
        if cache: Segment._cacheline(string, ln, file)

    def __len__(self):
        return len(self.string)

    def __contains__(self, key: str, /):
        return key in self.string

    def __getitem__(self, key: int | slice, /):
        string = self.string[key]
        start = (key.start or 0) if isinstance(key, slice) else key
        return Segment(string, self.ln + start, self.col, self.file, cache=False)

    def getline(self):
        return Segment._cache[self.file][self.ln]

    def lex(self):
        result = list[Segment]()
        i, start = 0, -1
        def append():
            nonlocal start
            if start >= 0:
                result.append(self[start:i])
                start = -1
        while i < len(self):
            match self[i]:
                case ' ' | '\t' | '\r' | '\n':
                    append()
                case '%':
                    append()
                    return result
                case '=' | '>' | '/' | '_':
                    append()
                    result.append(self[i])
                case ':' if self[i:i + 2] == '::':
                    append()
                    result.append(self[i:i + 2])
                    i += 1
                case _:
                    if start < 0:
                        start = i
            i += 1
        append()
        return result

    def __eq__(self, other: object, /):
        if isinstance(other, str):
            return self.string == other
        return super().__eq__(other)

    def __str__(self):
        return self.string

    _cache = dict[str, list[str]]()

    @staticmethod
    def _cacheline(string: str, ln: int, file: str):
        if file not in Segment._cache:
            Segment._cache[file] = []
        lines = Segment._cache[file]
        fill(lines, ln + 1, '')
        lines[ln] = string
