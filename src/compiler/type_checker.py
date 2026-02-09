import compiler.ast as ast
from compiler.types import Bool, FunType, Int, Type, Unit
from typing import Optional

class SymTab:
    def __init__(self, parent: Optional["SymTab"] = None):
        self.parent = parent
        self.table: dict[str, Type] = {}

    def define(self, name: str, value_type: Type) -> None:
        self.table[name] = value_type

    def lookup(self, name: str) -> Type:
        if name in self.table:
            return self.table[name]

        if self.parent is not None:
            return self.parent.lookup(name)

        raise TypeError(f"Undefined identifier '{name}'")

def setup_type_env() -> SymTab:
    env = SymTab()

    env.define("+", FunType((Int, Int), Int))
    env.define("-", FunType((Int, Int), Int))
    env.define("*", FunType((Int, Int), Int))
    env.define("/", FunType((Int, Int), Int))
    env.define("%", FunType((Int, Int), Int))

    env.define("<",  FunType((Int, Int), Bool))
    env.define("<=", FunType((Int, Int), Bool))
    env.define(">",  FunType((Int, Int), Bool))
    env.define(">=", FunType((Int, Int), Bool))

    env.define("and", FunType((Bool, Bool), Bool))
    env.define("or",  FunType((Bool, Bool), Bool))

    env.define("unary_-", FunType((Int,), Int))
    env.define("unary_not", FunType((Bool,), Bool))

    env.define("print_int",  FunType((Int,), Unit))
    env.define("print_bool", FunType((Bool,), Unit))
    env.define("read_int",   FunType((), Int))

    env.define("true", Bool)
    env.define("false", Bool)

    env.define("Int", Int)
    env.define("Bool", Bool)
    env.define("Unit", Unit)

    return env

env = setup_type_env()

def typecheck_helper(node: ast.Expression, env: SymTab) -> Type:
    match node:

        case ast.Literal():
            if isinstance(node.value, bool):
                return Bool
            elif isinstance(node.value, int):
                return Int
            else:
                raise TypeError(f"Unsupported literal: {node.value}")

        case ast.Identifier():
            value_type = env.lookup(node.name)
            return value_type

        case ast.UnaryOp():
            op_type = env.lookup(f"unary_{node.op}")
            if not isinstance(op_type, FunType):
                raise TypeError(f"'{node.op}' is not a unary operator")

            operand_type = typecheck(node.operand, env)
            expected_param_type = op_type.params[0]
            if expected_param_type != operand_type:
                raise TypeError(
                    f"Unary operator '{node.op}' expects operand of type {expected_param_type}, got {operand_type}"
                )

            return op_type.return_type

        case ast.BinaryOp() if node.op == "=":

            var = typecheck(node.left, env)
            value_type = typecheck(node.right, env)
            if var != value_type:
                raise TypeError(
                    f"Assignment expects value of type {var}, got {value_type}"
                )

            return value_type

        case ast.BinaryOp() if node.op in ("==", "!="):
            t1 = typecheck(node.left, env)
            t2 = typecheck(node.right, env)

            if t1 != t2:
                raise TypeError(
                    f"Operands of '{node.op}' must have the same type, got {t1} and {t2}"
                )

            return Bool

        case ast.BinaryOp():

            op_type = env.lookup(node.op)
            if not isinstance(op_type, FunType):
                raise TypeError(f"'{node.op}' is not a binary operator")

            t1 = typecheck(node.left, env)
            t2 = typecheck(node.right, env)

            expected_param_types = op_type.params
            if expected_param_types != (t1, t2):
                raise TypeError(
                    f"Operator '{node.op}' expects operands of type {expected_param_types}, got {t1} and {t2}"
                )

            return op_type.return_type

        case ast.IfThenElse():

            cond_type = typecheck(node.condition, env)
            if cond_type != Bool:
                raise TypeError("Condition of if-then-else must be of type Bool")

            then_type = typecheck(node.then_branch, env)

            if node.else_branch is not None:
                else_type = typecheck(node.else_branch, env)
                if then_type != else_type:
                    raise TypeError(
                        f"Then and else branches must have the same type, got {then_type} and {else_type}"
                    )

            return then_type

        case ast.WhileExpr():

            cond_type = typecheck(node.condition, env)
            if cond_type != Bool:
                raise TypeError("Condition of while must be of type Bool")

            typecheck(node.body, env)

            return Unit

        case ast.FunctionExpr():
            if len(node.arguments) > 6:
                raise TypeError("Functions with more than 6 arguments are not supported")

            assert isinstance(node.function_name, ast.Identifier)
            func_type = env.lookup(node.function_name.name)

            if not isinstance(func_type, FunType):
                raise TypeError(f"'{node.function_name.name}' is not a function")

            for arg, expected_type in zip(node.arguments, func_type.params):
                arg_type = typecheck(arg, env)
                if arg_type != expected_type:
                    raise TypeError(
                        f"Function '{node.function_name.name}' expects argument of type {expected_type}, got {arg_type}"
                    )

            return func_type.return_type

        case ast.BlockExpr():
            block_env = SymTab(parent=env)
            last_type: Type = Unit
            for stmt in node.statements:
                last_type = typecheck(stmt, block_env)
            return last_type

        case ast.FunctionTypeExpr():
            if node.param_types is not None and len(node.param_types) > 6:
                raise TypeError("Functions with more than 6 parameters are not supported")

            if node.param_types is not None:
                param_types = tuple(typecheck(param, env) for param in node.param_types)
            else:
                param_types = ()

            return_type = typecheck(node.return_type, env)

            return FunType(param_types, return_type)

        case ast.VarExpr():

            assert isinstance(node.name, str)
            name = node.name
            init_type = typecheck(node.initializer, env)

            if node.typed is not None:
                typed_type = typecheck(node.typed, env)
                if init_type != typed_type:
                    raise TypeError(
                        f"Variable '{name}' declared as type {typed_type}, but initialized with type {init_type}"
                    )

            env.define(name, init_type)
            return Unit

        case _:
            raise TypeError(f"Unknown AST node: {node}")

def typecheck(node: ast.Expression, env: SymTab) -> Type:
    t = typecheck_helper(node, env)
    node.type = t
    return t
