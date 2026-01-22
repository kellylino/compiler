from compiler.tokenizer import tokenize
from compiler.parser import parse
import compiler.ast as ast
import pytest

def test_parser_basics() -> None:

    result = parse(tokenize('a + b'))
    assert result == ast.BinaryOp(
        left=ast.Identifier('a'),
        op='+',
        right=ast.Identifier('b')
    )

def test_parser_associativity() -> None:

    result = parse(tokenize('1 - 2 + 3'))
    assert result == ast.BinaryOp(
        left=ast.BinaryOp(
            left=ast.Literal(1),
            op='-',
            right=ast.Literal(2)
        ),
        op='+',
        right=ast.Literal(3),
    )

def test_parser_precedence() -> None:

    result = parse(tokenize('a + b * c'))
    assert result == ast.BinaryOp(
        left=ast.Identifier('a'),
        op='+',
        right=ast.BinaryOp(
            left=ast.Identifier('b'),
            op='*',
            right=ast.Identifier('c')
        )
    )

def test_parser_parentheses() -> None:

    result = parse(tokenize('(a + b) * c'))
    assert result == ast.BinaryOp(
        left=ast.BinaryOp(
            left=ast.Identifier('a'),
            op='+',
            right=ast.Identifier('b')
        ),
        op='*',
        right=ast.Identifier('c')
    )

def test_garbage_at_end() -> None:

    with pytest.raises(Exception, match="unexpected token"):
        parse(tokenize('a + b c'))

    with pytest.raises(Exception, match="unexpected token"):
        parse(tokenize('1 2'))

    with pytest.raises(Exception, match="unexpected token"):
        parse(tokenize('(a + b) x'))

def test_empty_input() -> None:
    with pytest.raises(Exception, match="Empty input"):
        parse([])