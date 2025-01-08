class LanguageException(Exception):
    def exit(self):
        exit(f'{self.__class__.__name__}: {self}')

class RuleError(LanguageException):
    pass
