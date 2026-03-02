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

from dataclasses import dataclass

@dataclass
class TypeCheckState:
    has_return: bool = False

def typecheck_helper(node: ast.Expression, env: SymTab, state: TypeCheckState) -> Type:
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

            operand_type = typecheck_helper(node.operand, env, state)
            expected_param_type = op_type.params[0]
            if expected_param_type != operand_type:
                raise TypeError(
                    f"Unary operator '{node.op}' expects operand of type {expected_param_type}, got {operand_type}"
                )

            return op_type.return_type

        case ast.BinaryOp() if node.op == "=":

            var = typecheck_helper(node.left, env, state)
            value_type = typecheck_helper(node.right, env, state)
            if var != value_type:
                raise TypeError(
                    f"Assignment expects value of type {var}, got {value_type}"
                )

            return value_type

        case ast.BinaryOp() if node.op in ("==", "!="):
            t1 = typecheck_helper(node.left, env, state)
            t2 = typecheck_helper(node.right, env, state)

            if t1 != t2:
                raise TypeError(
                    f"Operands of '{node.op}' must have the same type, got {t1} and {t2}"
                )

            return Bool

        case ast.BinaryOp():
            op_type = env.lookup(node.op)
            if not isinstance(op_type, FunType):
                raise TypeError(f"'{node.op}' is not a binary operator")

            t1 = typecheck_helper(node.left, env, state)
            t2 = typecheck_helper(node.right, env, state)

            expected_param_types = op_type.params
            if expected_param_types != (t1, t2):
                raise TypeError(
                    f"Operator '{node.op}' expects operands of type {expected_param_types}, got {t1} and {t2}"
                )

            return op_type.return_type

        case ast.IfThenElse():

            cond_type = typecheck_helper(node.condition, env, state)
            if cond_type != Bool:
                raise TypeError("Condition of if-then-else must be of type Bool")

            then_type = typecheck_helper(node.then_branch, env, state)

            if node.else_branch is not None:
                else_type = typecheck_helper(node.else_branch, env, state)
                if then_type != else_type:
                    raise TypeError(
                        f"Then and else branches must have the same type, got {then_type} and {else_type}"
                    )

            return then_type

        case ast.WhileExpr():

            cond_type = typecheck_helper(node.condition, env, state)
            if cond_type != Bool:
                raise TypeError("Condition of while must be of type Bool")

            return_type = typecheck_helper(node.body, env, state)

            return return_type if state.has_return else Unit


        case ast.FunctionExpr():
            if len(node.arguments) > 6:
                raise TypeError("Functions with more than 6 arguments are not supported")

            assert isinstance(node.function_name, ast.Identifier)
            func_type = env.lookup(node.function_name.name)

            if not isinstance(func_type, FunType):
                raise TypeError(f"'{node.function_name.name}' is not a function")

            if len(node.arguments) != len(func_type.params):
                raise TypeError(
                    f"Function '{node.function_name.name}' expects {len(func_type.params)} "
                    f"parameter(s), but {len(node.arguments)} given"
                )

            for arg, expected_type in zip(node.arguments, func_type.params):
                arg_type = typecheck_helper(arg, env, state)
                if arg_type != expected_type:
                    raise TypeError(
                        f"Function '{node.function_name.name}' expects argument of type {expected_type}, got {arg_type}"
                    )

            return func_type.return_type

        case ast.BlockExpr():
            block_env = SymTab(parent=env)
            last_type: Type = Unit

            for stmt in node.statements:
                last_type = typecheck_helper(stmt, block_env, state)

            return last_type

        case ast.FunctionTypeExpr():
            if node.param_types is not None and len(node.param_types) > 6:
                raise TypeError("Functions with more than 6 parameters are not supported")

            if node.param_types is not None:
                param_types = tuple(typecheck_helper(param, env, state) for param in node.param_types)
            else:
                param_types = ()

            return_type = typecheck_helper(node.return_type, env, state)

            return FunType(param_types, return_type)

        case ast.VarExpr():

            assert isinstance(node.name, str)
            name = node.name
            init_type = typecheck_helper(node.initializer, env, state)

            if node.typed is not None:
                typed_type = typecheck_helper(node.typed, env, state)
                if init_type != typed_type:
                    raise TypeError(
                        f"Variable '{name}' declared as type {typed_type}, but initialized with type {init_type}"
                    )

            env.define(name, init_type)
            return Unit

        case ast.BreakExpr():
            return Unit

        case ast.ContinueExpr():
            return Unit

        case ast.ReturnExpr():
            state.has_return = True
            if node.result is not None:
                return_type = typecheck_helper(node.result, env, state)
                return return_type
            else:
                return Unit

        case ast.FunDefArgExpr():
            if not isinstance(node.name, ast.Identifier):
                raise TypeError(f"Parameter name must be an identifier, got {type(node.name)}")

            param_type = typecheck_helper(node.fun_type, env, state)

            return param_type

        case ast.FunDefExpr():
            if not isinstance(node.name, ast.Identifier):
                raise TypeError(f"Function name must be an identifier, got {type(node.name)}")

            func_name = node.name.name

            result_type = typecheck_helper(node.result_type, env, state)

            types: list[Type] = []
            param_env = SymTab(parent=env)

            for param in node.params:
                if not isinstance(param, ast.FunDefArgExpr):
                    raise TypeError(f"Function parameter must be FunDefArgExpr, got {type(param)}")

                if not isinstance(param.name, ast.Identifier):
                    raise TypeError(f"Parameter name must be an identifier, got {type(param.name)}")
                param_name = param.name.name

                param_type = typecheck_helper(param.fun_type, env, state)
                types.append(param_type)

                param_env.define(param_name, param_type)

            func_type = FunType(tuple(types), result_type)

            env.define(func_name, func_type)

            if isinstance(node.body, ast.BlockExpr) and node.body.statements:
            #     first_stmt = node.body.statements[0]
            #     if isinstance(first_stmt, ast.ReturnExpr):
            #         body_type = typecheck(first_stmt, param_env)
            #     else:
            #         body_type = typecheck(node.body, param_env)
            # else:
                body_type = typecheck_helper(node.body, param_env, state)

            if result_type != Unit and body_type != result_type:
                raise TypeError(
                    f"Function '{func_name}' body returns {body_type}, "
                    f"but declared to return {result_type}"
                )

            return result_type

        case ast.ModuleExpr():
            module_env = SymTab(parent=env)
            final_type: Type = Unit

            for item in node.items:
                if isinstance(item, ast.FunDefExpr):
                    if not isinstance(item.name, ast.Identifier):
                        raise TypeError(f"Function name must be an identifier, got {type(item.name)}")

                    func_name = item.name.name

                    result_type = typecheck_helper(item.result_type, env, state)

                    param_types_list: list[Type] = []
                    for param in item.params:
                        if not isinstance(param, ast.FunDefArgExpr):
                            raise TypeError(f"Function parameter must be FunDefArgExpr, got {type(param)}")

                        param_type = typecheck_helper(param.fun_type, env, state)
                        param_types_list.append(param_type)

                    func_type = FunType(tuple(param_types_list), result_type)
                    module_env.define(func_name, func_type)

            for item in node.items:
                if isinstance(item, ast.FunDefExpr):
                    final_type = typecheck_helper(item, module_env, state)
                else:
                    final_type = typecheck_helper(item, module_env, state)

            return final_type

        case _:
            raise TypeError(f"Unknown AST node: {node}")

def typecheck(node: ast.Expression, env: SymTab) -> Type:
    state = TypeCheckState()
    t = typecheck_helper(node, env, state)
    node.type = t
    return t
