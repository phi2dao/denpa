from .segment import Segment

class DenpaError(Exception):
    def exit(self):
        exit(f'{self.__class__.__name__}: {self}')

class ErrorWithSegment(DenpaError):
    def __init__(self, message: str, *segments: Segment, highlight = True):
        self.segments = segments
        self.highlight = highlight
        super().__init__(message)

    def __str__(self):
        if not self.segments:
            return super().__str__()
        msg = f'{super().__str__()} in "{self.segments[0].file}", line {self.segments[0].ln + 1}'
        line = self.segments[0].getline()
        msg += f'\n  {line}'
        if self.highlight:
            msg += f'\n  {self._highlight(line)}'
        return msg

    def _highlight(self, line: str):
        result = [' '] * len(line)
        for i in range(len(line)):
            for seg in self.segments:
                if i >= seg.col and i < seg.col + len(seg):
                    result[i] = '^'
        return ''.join(result)

class ParseError(ErrorWithSegment): pass
class SoundChangeError(ErrorWithSegment): pass
