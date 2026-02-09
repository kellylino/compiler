from typing import Any, Optional
from compiler import ast
from compiler.parser import parse
from compiler.tokenizer import tokenize

class SymTab:
    def __init__(self, parent: Optional["SymTab"] = None):
        self.parent = parent
        self.table: dict[str, Any] = {}

    def define(self, name: str, value: Any) -> None:
        self.table[name] = value

    def lookup(self, name: str) -> Any:
        if name in self.table:
            return self.table[name]

        if self.parent is not None:
            return self.parent.lookup(name)

        raise NameError(f"Undefined variable '{name}'")

    def assign(self, name: str, value: Any) -> None:
        if name in self.table:
            self.table[name] = value
            return

        if self.parent is not None:
            self.parent.assign(name, value)
            return

        raise NameError(f"Undefined variable '{name}'")

def setup_global_env() -> SymTab:
    env = SymTab()
    def unary_minus(x: Value) -> Value:
        if isinstance(x, int) and not isinstance(x, bool):
            return -x
        raise TypeError("Unary '-' requires int")

    def unary_not(x: Value) -> Value:
        if isinstance(x, bool):
            return not x
        raise TypeError("Unary 'not' requires bool")

    def add(a: Value, b: Value) -> Value:
        if isinstance(a, int) and not isinstance(a, bool) and \
        isinstance(b, int) and not isinstance(b, bool):
            return a + b
        raise TypeError("'+' requires ints")

    def minus(a: Value, b: Value) -> Value:
        if isinstance(a, int) and isinstance(b, int):
            return a - b
        raise TypeError("'-' requires ints")

    def mul(a: Value, b: Value) -> Value:
        if isinstance(a, int) and isinstance(b, int):
            return a * b
        raise TypeError("'*' requires ints")

    def div(a: Value, b: Value) -> Value:
        if isinstance(a, int) and isinstance(b, int):
            return a // b
        raise TypeError("'/' requires ints")

    def mudo(a: Value, b: Value) -> Value:
        if isinstance(a, int) and isinstance(b, int):
            return a % b
        raise TypeError("'%' requires ints")

    def less_than(a: Value, b: Value) -> Value:
        if isinstance(a, int) and isinstance(b, int):
            return a < b
        raise TypeError("'<' requires ints")

    def less_than_equal(a: Value, b: Value) -> Value:
        if isinstance(a, int) and isinstance(b, int):
            return a <= b
        raise TypeError("'<=' requires ints")

    def large_than(a: Value, b: Value) -> Value:
        if isinstance(a, int) and isinstance(b, int):
            return a > b
        raise TypeError("'>' requires ints")

    def large_than_equal(a: Value, b: Value) -> Value:
        if isinstance(a, int) and isinstance(b, int):
            return a >= b
        raise TypeError("'>=' requires ints")

    def equal_to(a: Value, b: Value) -> Value:
        if isinstance(a, int) and isinstance(b, int):
            return a == b
        raise TypeError("'==' requires ints")

    def not_equal_to(a: Value, b: Value) -> Value:
        if isinstance(a, int) and isinstance(b, int):
            return a != b
        raise TypeError("'!=' requires ints")

    env.define("+", add)
    env.define("-", minus)
    env.define("*", mul)
    env.define("/", div)
    env.define("%", mudo)
    env.define("==", equal_to)
    env.define("!=", not_equal_to)
    env.define("<", less_than)
    env.define("<=", less_than_equal)
    env.define(">", large_than)
    env.define(">=", large_than_equal)
    env.define("unary_-", unary_minus)
    env.define("unary_not", unary_not)

    env.define("print_int", lambda x: print(x))
    env.define("print_bool", lambda x: print("true" if x else "false"))
    env.define("read_int", lambda: int(input()))

    env.define("true", True)
    env.define("false", False)
    env.define("Int", "Int")
    env.define("Bool", "Bool")
    env.define("Unit", "Unit")

    return env

type Value = int | bool | str | None

env = setup_global_env()

def interpret(node: ast.Expression, env: SymTab) -> Value:
    match node:

        case ast.Literal():
            return node.value

        case ast.Identifier():
            value = env.lookup(node.name)
            return value

        case ast.UnaryOp():
            operand = interpret(node.operand, env)
            func = env.lookup(f"unary_{node.op}")
            if not callable(func):
                raise TypeError(f"'{node.op}' is not a unary operator")
            return func(operand)

        case ast.BinaryOp() if node.op == "or":
            left = interpret(node.left, env)
            if not isinstance(left, bool):
                raise TypeError("'or' requires booleans")
            if left is True:
                return True
            return interpret(node.right, env)

        case ast.BinaryOp() if node.op == "and":
            left = interpret(node.left, env)
            if not isinstance(left, bool):
                raise TypeError("'and' requires booleans")
            if left is False:
                return False
            return interpret(node.right, env)

        case ast.BinaryOp() if node.op == "=":
            if not isinstance(node.left, ast.Identifier):
                raise TypeError("Left-hand side of assignment must be an identifier")
            value = interpret(node.right, env)
            env.assign(node.left.name, value)
            return value

        case ast.BinaryOp():
            left = interpret(node.left, env)
            right = interpret(node.right, env)
            func = env.lookup(node.op)
            if not callable(func):
                raise TypeError(f"'{node.op}' is not a binary operator")
            return func(left, right)

        case ast.IfThenElse():
            cond = interpret(node.condition, env)
            if not isinstance(cond, bool):
                    raise TypeError(f"cond should be either true or false")

            if cond:
                return interpret(node.then_branch, env)
            else:
                if node.else_branch is None:
                    return None
                return interpret(node.else_branch, env)

        case ast.WhileExpr():
            result: Value = None
            while interpret(node.condition, env):
                result = interpret(node.body, env)
            return result

        case ast.FunctionExpr():
            assert isinstance(node.function_name, ast.Identifier)
            func = env.lookup(node.function_name.name)

            if not callable(func):
                raise NameError(f"'{node.function_name.name}' is not callable")
            args = [interpret(arg, env) for arg in node.arguments]
            return func(*args)

        case ast.BlockExpr():
            block_env = SymTab(parent=env)
            block_result: Value = None
            for stmt in node.statements:
                block_result = interpret(stmt, block_env)
            return block_result

        case ast.VarExpr():
            assert isinstance(node.name, str)
            name = node.name
            value = interpret(node.initializer, env)
            env.define(name, value)

            return value

        case _:
            raise NotImplementedError(
                f"Interpreter not implemented for {type(node).__name__}"
            )