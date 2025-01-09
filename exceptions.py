from typing import TYPE_CHECKING
if TYPE_CHECKING: from .parser import Parser, Token

class LanguageException(Exception):
    def exit(self):
        msgs: list[str] = []
        e = self
        while e:
            msgs.append(f'{e.__class__.__name__}: {e}')
            e = e.__cause__
        exit('\n\n'.join(reversed(msgs)))

class RuleError(LanguageException):
    pass

class ParseError(LanguageException):
    def __init__(self, message: str, /, parser: 'Parser', token: 'Token'):
        self.message = message
        self.parser = parser
        self.token = token
        super().__init__(message, parser, token)

    def __str__(self):
        template = '{} in file "{}", line {}\n  {}\n  {}'
        line = self.parser.lines[self.token.ln]
        under = ' ' * self.token.col + '^' * len(self.token)
        return template.format(self.message, self.parser.file, self.token.ln + 1, line, under)

class ImportError(ParseError):
    pass
