from compiler.tokenizer import tokenize, L
from compiler.interpreter import interpret, setup_global_env
from compiler.parser import parse
import compiler.ast as ast
from pytest import MonkeyPatch
import pytest

#helper functions:
def Literal(value: int) -> ast.Literal:
    return ast.Literal(loc=L, value=value)

def Identifier(name: str) -> ast.Identifier:
    return ast.Identifier(loc=L, name=name)

def BinaryOp(left: ast.Expression, op: str, right: ast.Expression) -> ast.BinaryOp:
    return ast.BinaryOp(loc=L, left=left, op=op, right=right)

def IfThenElse(condition:ast.Expression, then_branch:ast.Expression, else_branch:ast.Expression | None) -> ast.IfThenElse:
    return ast.IfThenElse(loc=L, condition=condition, then_branch=then_branch, else_branch=else_branch)

def WhileExpr(condition:ast.Expression, body:ast.Expression) -> ast.WhileExpr:
    return ast.WhileExpr(loc=L, condition=condition, body=body)

def FunctionExpr(function_name:ast.Expression, arguments: list[ast.Expression]) -> ast.FunctionExpr:
    return ast.FunctionExpr(loc=L, function_name=function_name, arguments=arguments)

def UnaryOp(op:str, operand:ast.Expression) -> ast.UnaryOp:
    return ast.UnaryOp(loc=L, op=op, operand=operand)

def BlockExpr(statements:list[ast.Expression]) -> ast.BlockExpr:
    return ast.BlockExpr(loc=L, statements=statements)

def VarExpr(name:ast.Expression, typed: ast.Expression | None, initializer:ast.Expression) -> ast.VarExpr:
    return ast.VarExpr(loc=L, name=name, typed=typed, initializer=initializer)

def test_interpret_basics() -> None:
    env = setup_global_env()

    with pytest.raises(Exception, match="Undefined variable"):
        interpret(parse(tokenize('a + b')), env)

    result = interpret(parse(tokenize('2 + 3')), env)
    assert result == 5

    result = interpret(parse(tokenize('var a = 2 + 3')), env)
    assert result == 5

def test_arithmetic_ops() -> None:
    env = setup_global_env()

    assert interpret(parse(tokenize("1 + 2")), env) == 3
    assert interpret(parse(tokenize("5 - 3")), env) == 2
    assert interpret(parse(tokenize("4 * 3")), env) == 12
    assert interpret(parse(tokenize("8 / 2")), env) == 4
    assert interpret(parse(tokenize("7 % 4")), env) == 3

    with pytest.raises(TypeError):
        interpret(parse(tokenize("1 + true")), env)

def test_unary_ops() -> None:
    env = setup_global_env()

    assert interpret(parse(tokenize("-5")), env) == -5
    assert interpret(parse(tokenize("not false")), env) is True
    assert interpret(parse(tokenize("not true")), env) is False

    with pytest.raises(TypeError):
        interpret(parse(tokenize("-true")), env)

def test_comparisons() -> None:
    env = setup_global_env()

    assert interpret(parse(tokenize("1 < 2")), env) is True
    assert interpret(parse(tokenize("2 <= 2")), env) is True
    assert interpret(parse(tokenize("3 > 1")), env) is True
    assert interpret(parse(tokenize("3 >= 4")), env) is False
    assert interpret(parse(tokenize("2 == 2")), env) is True
    assert interpret(parse(tokenize("2 != 3")), env) is True

def test_variables_and_assignment() -> None:
    env = setup_global_env()

    result = interpret(parse(tokenize("var x = 5; x")), env)
    assert result == 5

    result = interpret(parse(tokenize("var x = 1; x = 2; x")), env)
    assert result == 2

    with pytest.raises(TypeError):
        interpret(parse(tokenize("1 = 2")), env)

def test_block_scope() -> None:
    env = setup_global_env()

    exp = """
    {
        var x = 1;
        {
            var x = 2;
            x
        };
        x
    }
    """
    result = interpret(parse(tokenize(exp)), env)
    assert result == 1

def test_if_then_else() -> None:
    env = setup_global_env()

    assert interpret(parse(tokenize("if true then 1 else 2")), env) == 1
    assert interpret(parse(tokenize("if false then 1 else 2")), env) == 2
    assert interpret(parse(tokenize("if false then 1")), env) is None

    with pytest.raises(TypeError):
        interpret(parse(tokenize("if 1 then 2 else 3")), env)

def test_while_loop() -> None:
    env = setup_global_env()

    exp = """
    var x = 0;
    while x < 3 do x = x + 1;
    x
    """
    result = interpret(parse(tokenize(exp)), env)
    assert result == 3

def test_short_circuit_or() -> None:
    env = setup_global_env()

    exp = """
    var rhs = false;
    true or { rhs = true; true };
    rhs
    """
    result = interpret(parse(tokenize(exp)), env)
    assert result is False


def test_short_circuit_and() -> None:
    env = setup_global_env()

    exp = """
    var rhs = false;
    false and { rhs = true; true };
    rhs
    """
    result = interpret(parse(tokenize(exp)), env)
    assert result is False

def test_builtin_functions(capsys: pytest.CaptureFixture[str]) -> None:
    env = setup_global_env()

    interpret(parse(tokenize("print_int(5)")), env)
    captured = capsys.readouterr()
    assert captured.out.strip() == "5"

    interpret(parse(tokenize("print_bool(true)")), env)
    captured = capsys.readouterr()
    assert captured.out.strip() == "true"

def test_errors() -> None:
    env = setup_global_env()

    with pytest.raises(NameError):
        interpret(parse(tokenize("x")), env)

    with pytest.raises(NameError):
        interpret(parse(tokenize("x + 1")), env)

def test_collatz_program(capsys: pytest.CaptureFixture[str], monkeypatch: MonkeyPatch) -> None:
    env = setup_global_env()

    # Mock input() so read_int() returns 6
    monkeypatch.setattr("builtins.input", lambda: "6")

    program = """
        var n: Int = read_int();
        print_int(n);
        while n > 1 do {
            if n % 2 == 0 then {
                n = n / 2;
            } else {
                n = 3*n + 1;
            }
            print_int(n);
        }
    """

    result = interpret(parse(tokenize(program)), env)

    captured = capsys.readouterr().out.strip().splitlines()

    assert captured == [
        "6",
        "3",
        "10",
        "5",
        "16",
        "8",
        "4",
        "2",
        "1",
    ]

def test_assignment_in_function_updates_outer_scope(capsys: pytest.CaptureFixture[str]) -> None:
    env = setup_global_env()

    program = """
        var x = 1;
        x = 2;
        print_int(x)
    """

    interpret(parse(tokenize(program)), env)

    captured = capsys.readouterr().out.strip()
    assert captured == "2"
