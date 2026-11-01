import re
from abc import ABCMeta, abstractmethod
from typing import Iterator, Mapping, Optional, Pattern

_posix_variable: Pattern[str] = re.compile(
    r"""
    \$\{
        (?P<name>[^\}:]*)
        (?::-
            (?P<default>[^\}]*)
        )?
    \}
    """,
    re.VERBOSE,
)


class UndefinedVariableError(ValueError):
    """A recognized variable reference is absent from the resolution mapping."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Undefined variable: {name}")


class Atom(metaclass=ABCMeta):
    def __ne__(self, other: object) -> bool:
        result = self.__eq__(other)
        if result is NotImplemented:
            return NotImplemented
        return not result

    @abstractmethod
    def resolve(self, env: Mapping[str, Optional[str]]) -> str: ...


class Literal(Atom):
    def __init__(self, value: str) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"Literal(value={self.value})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.value == other.value

    def __hash__(self) -> int:
        return hash((self.__class__, self.value))

    def resolve(self, env: Mapping[str, Optional[str]]) -> str:
        return self.value


class Variable(Atom):
    def __init__(self, name: str, default: Optional[str], strict: bool = False) -> None:
        self.name = name
        self.default = default
        self.strict = strict

    def __repr__(self) -> str:
        return f"Variable(name={self.name}, default={self.default})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return (self.name, self.default, self.strict) == (other.name, other.default, other.strict)

    def __hash__(self) -> int:
        return hash((self.__class__, self.name, self.default, self.strict))

    def resolve(self, env: Mapping[str, Optional[str]]) -> str:
        if self.strict and self.default is None and self.name not in env:
            raise UndefinedVariableError(self.name)
        default = self.default if self.default is not None else ""
        result = env.get(self.name, default)
        return result if result is not None else ""


def parse_variables(value: str, strict: bool = False) -> Iterator[Atom]:
    cursor = 0

    for match in _posix_variable.finditer(value):
        (start, end) = match.span()
        name = match["name"]
        default = match["default"]

        if start > cursor:
            yield Literal(value=value[cursor:start])

        yield Variable(name=name, default=default, strict=strict)
        cursor = end

    length = len(value)
    if cursor < length:
        yield Literal(value=value[cursor:length])
