from typing import Optional, TypeVar, Generic
from compiler import ast, ir
from compiler.types import Bool, Int, Type, Unit

T = TypeVar('T')

class SymTab(Generic[T]):
    def __init__(self, parent: Optional["SymTab[T]"] = None):
        self.parent = parent
        self.table: dict[str, T] = {}

    def add_local(self, name: str, value: T) -> None:
        self.table[name] = value

    def require(self, name: str) -> T:
        if name in self.table:
            return self.table[name]

        if self.parent is not None:
            return self.parent.require(name)

        raise KeyError(f"Undefined identifier '{name}'")

    def assign(self, name: str, value: T) -> None:
        if name in self.table:
            self.table[name] = value
            return

        if self.parent is not None:
            self.parent.assign(name, value)
            return

        raise KeyError(f"Undefined identifier '{name}'")

def generate_ir(
    # 'reserved_names' should contain all global names
    # like 'print_int' and '+'. You can get them from
    # the global symbol table of your interpreter or type checker.
    reserved_names: set[str],
    root_expr: ast.Expression
) -> list[ir.Instruction]:
    # 'var_unit' is used when an expression's type is 'Unit'.
    var_unit = ir.IRVar('unit')

    var_counter = 1
    def new_var() -> ir.IRVar:
        """Generates a new unique IR variable."""
        nonlocal var_counter
        if var_counter == 1:
            var_name = 'x'
        else:
            var_name = f'x{var_counter}'
        var_counter += 1
        return ir.IRVar(var_name)

    lable_counter = 1
    lable = []
    def new_label(loc: ast.Location, base_name: str) -> ir.Label:
        """Generates a new unique IR label."""
        nonlocal lable_counter

        if base_name not in lable:
            label_name = f'{base_name}'
        else:
            label_name = f'{base_name}{lable_counter+1}'

        lable.append(label_name)
        return ir.Label(loc,label_name)

    # We collect the IR instructions that we generate into this list.
    ins: list[ir.Instruction] = []

    # This function visits an AST node,
    # appends IR instructions to 'ins',
    # and returns the IR variable where
    # the emitted IR instructions put the result.
    #
    # It uses a symbol table to map local variables
    # (which may be shadowed) to unique IR variables.
    # The symbol table will be updated in the same way as
    # in the interpreter and type checker.
    def visit(st: SymTab[ir.IRVar], expr: ast.Expression) -> ir.IRVar:
        loc = expr.loc

        match expr:
            case ast.Literal():
                # Create an IR variable to hold the value,
                # and emit the correct instruction to
                # load the constant value.
                match expr.value:
                    case bool():
                        var = new_var()
                        ins.append(ir.LoadBoolConst(
                            loc, expr.value, var))
                    case int():
                        var = new_var()
                        ins.append(ir.LoadIntConst(
                            loc, expr.value, var))
                    case None:
                        var = var_unit
                    case _:
                        raise Exception(f"{loc}: unsupported literal: {type(expr.value)}")

                return var

            case ast.Identifier():
                # Look up the IR variable that corresponds to the source code variable.
                if expr.name == "true":
                    var = new_var()
                    ins.append(ir.LoadBoolConst(expr.loc, True, var))
                    return var
                elif expr.name == "false":
                    var = new_var()
                    ins.append(ir.LoadBoolConst(expr.loc, False, var))
                    return var
                return st.require(expr.name)

            case ast.UnaryOp():
                var_op = st.require(f'unary_{expr.op}')
                var_operand = visit(st, expr.operand)
                var_result = new_var()
                ins.append(ir.Call(
                    loc, var_op, [var_operand], var_result))
                return var_result

            case ast.BinaryOp() if expr.op == "=":
                var_left = visit(st, expr.left)
                var_right = visit(st, expr.right)
                ins.append(ir.Copy(loc, var_right, var_left))
                return var_left

            case ast.BinaryOp() if expr.op == "or":
                # Short-circuiting 'or' can be implemented using a conditional jump.
                l_right = new_label(expr.right.loc, 'or_right')
                l_end = new_label(expr.right.loc,'or_end')
                l_skip= new_label(expr.right.loc,'or_skip')

                var_left = visit(st, expr.left)
                ins.append(ir.CondJump(loc, var_left, l_skip, l_right))

                ins.append(l_right)
                var_right = visit(st, expr.right)
                var_result = new_var()
                ins.append(ir.Copy(loc, var_right, var_result))
                ins.append(ir.Jump(loc, l_end))

                ins.append(l_skip)
                ins.append(ir.LoadBoolConst(loc, True, var_result))
                ins.append(ir.Jump(loc, l_end))

                ins.append(l_end)

                return var_result

            case ast.BinaryOp() if expr.op == "and":
                # Short-circuiting 'and' can be implemented using a conditional jump.
                l_right = new_label(expr.right.loc,'and_right')
                l_end = new_label(expr.right.loc, 'and_end')
                l_skip = new_label(expr.right.loc, 'and_skip')

                var_left = visit(st, expr.left)
                ins.append(ir.CondJump(loc, var_left, l_right, l_skip))

                ins.append(l_right)
                var_right = visit(st, expr.right)
                var_result = new_var()
                ins.append(ir.Copy(loc, var_right, var_result))
                ins.append(ir.Jump(loc, l_end))

                ins.append(l_skip)
                ins.append(ir.LoadBoolConst(loc, False, var_result))
                ins.append(l_end)

                return var_result

            case ast.BinaryOp():
                # Ask the symbol table to return the variable that refers to the operator to call.
                var_op = st.require(expr.op)
                # Recursively emit instructions to calculate the operands.
                var_left = visit(st, expr.left)
                var_right = visit(st, expr.right)
                # Generate variable to hold the result.
                var_result = new_var()
                # Emit a Call instruction that writes to that variable.
                ins.append(ir.Call(
                    loc, var_op, [var_left, var_right], var_result))
                return var_result

            case ast.IfThenElse():
                if expr.else_branch is None:
                    # Create (but don't emit) some jump targets.
                    l_then = new_label(expr.then_branch.loc, 'then')
                    l_end = new_label(expr.loc, 'if_end')

                    # Recursively emit instructions for
                    # evaluating the condition.
                    var_cond = visit(st, expr.condition)
                    # Emit a conditional jump instruction
                    # to jump to 'l_then' or 'l_end',
                    # depending on the content of 'var_cond'.
                    ins.append(ir.CondJump(loc, var_cond, l_then, l_end))

                    # Emit the label that marks the beginning of
                    # the "then" branch.
                    ins.append(l_then)
                    # Recursively emit instructions for the "then" branch.
                    visit(st, expr.then_branch)

                    # Emit the label that we jump to
                    # when we don't want to go to the "then" branch.
                    ins.append(l_end)

                    # An if-then expression doesn't return anything, so we
                    # return a special variable "unit".
                    return var_unit
                else:
                    # Similar to the above, but we also need to handle the "else" branch,
                    # and we need to generate a variable to hold the result of the whole expression.
                    l_then = new_label(expr.then_branch.loc, 'then')
                    l_else = new_label(expr.else_branch.loc, 'else')
                    l_end = new_label(expr.loc, 'if_end')

                    var_cond = visit(st, expr.condition)
                    ins.append(ir.CondJump(loc, var_cond, l_then, l_else))

                    var_result = new_var()

                    ins.append(l_then)
                    var_then = visit(st, expr.then_branch)
                    ins.append(ir.Copy(loc, var_then, var_result))
                    ins.append(ir.Jump(loc, l_end))

                    ins.append(l_else)
                    var_else = visit(st, expr.else_branch)
                    ins.append(ir.Copy(loc, var_else, var_result))

                    ins.append(l_end)

                    return var_result

            case ast.WhileExpr():
                l_start = new_label(expr.loc, 'while_start')
                ins.append(l_start)
                l_body = new_label(expr.body.loc, 'while_body')
                l_end = new_label(expr.loc, 'while_end')

                var_cond = visit(st, expr.condition)
                ins.append(ir.CondJump(loc, var_cond, l_body, l_end))

                ins.append(l_body)
                visit(st, expr.body)
                ins.append(ir.Jump(loc, l_start))
                ins.append(l_end)
                return var_unit

            case ast.FunctionExpr():
                var_fun = visit(st, expr.function_name)
                var_args = [visit(st, arg) for arg in expr.arguments]
                var_result = new_var()
                ins.append(ir.Call(loc, var_fun, var_args, var_result))
                return var_result

            case ast.BlockExpr():
                block_st = SymTab(parent=st)
                last_var = var_unit
                for stmt in expr.statements:
                    last_var = visit(block_st, stmt)
                return var_unit if expr.type == Unit else last_var

            case ast.VarExpr():
                if expr.name in st.table:
                    raise Exception(f"{loc}: Variable '{expr.name}' is already declared in this scope")

                initializer_var = visit(st, expr.initializer)

                var_a = new_var()
                ins.append(ir.Copy(loc, initializer_var, var_a))

                st.add_local(expr.name, var_a)

                return var_unit

            case _:
                raise Exception(f"{loc}: Unsupported expression {type(expr)}")


    # We start with a SymTab that maps all available global names
    # like 'print_int' to IR variables of the same name.
    # In the Assembly generator stage, we will give
    # actual implementations for these globals. For now,
    # they just need to exist so the variable lookups work,
    # and clashing variable names can be avoided.
    root_symtab = SymTab[ir.IRVar](parent=None)
    for name in reserved_names:
        root_symtab.add_local(name, ir.IRVar(name))

    # Start visiting the AST from the root.
    var_final_result = visit(root_symtab, root_expr)

    # Add IR code to print the result, based on the type assigned earlier by the type checker.
    if root_expr.type == Int:
        ins.append(ir.Call(
            root_expr.loc, ir.IRVar('print_int'), [var_final_result], new_var()))
    elif root_expr.type == Bool:
        ins.append(ir.Call(
            root_expr.loc, ir.IRVar('print_bool'), [var_final_result], new_var()))

    return ins

reserved_names = {
    '+', '-', '*', '/', '%',
    '<', '<=', '>', '>=',
    '==', '!=', '=',
    'and', 'or',
    'unary_-',
    'unary_not',
    'print_int',
    'print_bool',
    'read_int',
    'true', 'false',
    'Int', 'Bool', 'Unit'
}

from compiler.parser import parse
from compiler.tokenizer import tokenize
from compiler.type_checker import typecheck, setup_type_env
if __name__ == "__main__":
    # expr = parse(tokenize("""
    #     var n: Int = read_int();
    #     print_int(n);
    #     while n > 1 do {
    #         if n % 2 == 0 then {
    #             n = n / 2;
    #         } else {
    #             n = 3 * n + 1;
    #         }
    #         print_int(n);
    #     }
    # """))
    expr = parse(tokenize('true or false'))
    env = setup_type_env()
    typecheck(expr, env)

    ins = generate_ir(reserved_names, expr)
    for i in ins:
        print(i)