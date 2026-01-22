import re
from typing import Literal, Union
from dataclasses import dataclass

TokenType = Literal['int_literal', 'identifier', 'operators', 'punctuation', 'other', 'end']

class SpecialLocation:
    def __eq__(self, other: object) -> bool:
        return True

L = SpecialLocation()

@dataclass
class Location:
    line: int
    column: int

@dataclass
class Token:
    text: str
    type: Literal['int_literal', 'identifier', 'operators', 'punctuation', 'other', 'end']
    loc: Union[Location, SpecialLocation]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Token):
            if self.text != other.text or self.type != other.type:
                return False

            return (self.loc == L or other.loc == L or self.loc == other.loc)
        return False

def tokenize(source_code: str) -> list[Token]:
    tokens = []

    identifiers = re.compile(r'[a-zA-Z_][a-zA-Z0-9_]*')
    non_negative_integer = re.compile(r'[0-9][0-9]*')
    operators = re.compile(r'==|!=|<=|>=|\+|\-|\*|/|%|=|<|>')
    punctuation = re.compile(r'[\(\)\{\},;]')

    patterns: list[tuple[re.Pattern[str], TokenType]] = [
        (identifiers, 'identifier'),
        (non_negative_integer, 'int_literal'),
        (operators, 'operators'),
        (punctuation, 'punctuation')
    ]

    i = 0
    line = 1
    column = 1
    while i < len(source_code):
        char = source_code[i]

        if char == '\n':
            line += 1
            column = 1
            i += 1
            continue

        if char.isspace():
            column += 1
            i += 1
            continue

        if source_code.startswith('//', i) or source_code.startswith('#', i):
            while i < len(source_code) and source_code[i] != '\n':
                i += 1
            continue

        loc = Location(line, column)

        matched = False
        for pattern, token_type in patterns:
            match = pattern.match(source_code, i)
            if match:
                text = match.group(0)
                tokens.append(Token(text, token_type, loc))

                i += len(text)
                column += len(text)
                matched = True
                break

        if not matched:
            tokens.append(Token(char, 'other', loc))
            i += 1
            column += 1

    return tokens
