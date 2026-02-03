from compiler.tokenizer import tokenize, L
from compiler.parser import parse
import compiler.ast as ast
import pytest
from compiler.type_checker import setup_type_env, typecheck
from compiler.types import Bool, FunType, Int, Type, Unit

env = setup_type_env()

def test_typecheck_basics() -> None:
    ast_node = parse(tokenize("1 + 2"))
    result = typecheck(ast_node, env)

    assert result is Int
    assert ast_node.type is Int

def test_typecheck_comparison() -> None:
    ast_node = parse(tokenize("1 < 2"))
    result = typecheck(ast_node, env)

    assert result is Bool
    assert ast_node.type is Bool

def test_typecheck_unary() -> None:
    ast_node = parse(tokenize("-1"))
    result = typecheck(ast_node, env)

    assert result is Int
    assert ast_node.type is Int

def test_typecheck_if() -> None:
    ast_node = parse(tokenize("if true then 1 else 2"))
    result = typecheck(ast_node, env)

    assert result is Int
    assert ast_node.type is Int

def test_typecheck_while() -> None:
    ast_node = parse(tokenize("while true do 1"))
    result = typecheck(ast_node, env)

    assert result is Unit
    assert ast_node.type is Unit

def test_type_block() -> None:
    ast_node = parse(tokenize("{ var f: (Int) => Unit = print_int; f(123)}"))
    result = typecheck(ast_node, env)

    assert result is Unit
    assert ast_node.type is Unit


def test_type_error_addition() -> None:
    ast_node = parse(tokenize("1 + true"))

    with pytest.raises(TypeError):
        typecheck(ast_node, env)

def test_type_error_if_condition() -> None:
    ast_node = parse(tokenize("if 1 then 2 else 3"))

    with pytest.raises(TypeError):
        typecheck(ast_node, env)

