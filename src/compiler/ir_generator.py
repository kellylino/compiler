from typing import Optional, TypeVar, Generic
from compiler import ast, ir
from compiler.types import Bool, Int, Type, Unit

T = TypeVar('T')

class SymTab(Generic[T]):
    loop_start: Optional[ir.Label]
    loop_end: Optional[ir.Label]

    def __init__(self, parent: Optional["SymTab[T]"] = None):
        self.parent = parent
        self.table: dict[str, T] = {}
        if parent:
            self.loop_start = parent.loop_start
            self.loop_end = parent.loop_end
        else:
            self.loop_start = None
            self.loop_end = None

    def add_local(self, name: str, value: T) -> None:
        self.table[name] = value

    def require(self, name: str) -> T:
        if name in self.table:
            return self.table[name]

        if self.parent is not None:
            return self.parent.require(name)

        raise KeyError(f"Undefined identifier '{name}'")

    def enter_loop(self, start: ir.Label, end: ir.Label) -> None:
        self.loop_start = start
        self.loop_end = end

    def exit_loop(self) -> None:
        if self.parent:
            self.loop_start = self.parent.loop_start
            self.loop_end = self.parent.loop_end
        else:
            self.loop_start = None
            self.loop_end = None

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
) -> dict[str, list[ir.Instruction]]:
    # 'var_unit' is used when an expression's type is 'Unit'.
    var_unit = ir.IRVar('unit')
    var_unit_return = ir.IRVar('None')

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

    ins: dict[str, list[ir.Instruction]] = {}

    current_function = "main"
    in_function_def = False

    def emit(insn: ir.Instruction) -> None:
        if current_function not in ins:
            ins[current_function] = []
        ins[current_function].append(insn)

    def visit(st: SymTab[ir.IRVar], expr: ast.Expression) -> ir.IRVar:
        nonlocal current_function, var_counter
        loc = expr.loc

        match expr:
            case ast.Literal():
                # Create an IR variable to hold the value,
                # and emit the correct instruction to
                # load the constant value.
                match expr.value:
                    case bool():
                        var = new_var()
                        emit(ir.LoadBoolConst(
                            loc, expr.value, var))
                    case int():
                        var = new_var()
                        emit(ir.LoadIntConst(
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
                    emit(ir.LoadBoolConst(expr.loc, True, var))
                    return var
                elif expr.name == "false":
                    var = new_var()
                    emit(ir.LoadBoolConst(expr.loc, False, var))
                    return var
                return st.require(expr.name)

            case ast.UnaryOp():
                var_op = st.require(f'unary_{expr.op}')
                var_operand = visit(st, expr.operand)
                var_result = new_var()
                emit(ir.Call(
                    loc, var_op, [var_operand], var_result))
                return var_result

            case ast.BinaryOp() if expr.op == "=":
                var_left = visit(st, expr.left)
                var_right = visit(st, expr.right)
                emit(ir.Copy(loc, var_right, var_left))
                return var_left

            case ast.BinaryOp() if expr.op == "or":
                l_right = new_label(expr.right.loc, 'or_right')
                l_end = new_label(expr.right.loc,'or_end')
                l_skip= new_label(expr.right.loc,'or_skip')

                var_left = visit(st, expr.left)
                emit(ir.CondJump(loc, var_left, l_skip, l_right))

                emit(l_right)
                var_right = visit(st, expr.right)
                var_result = new_var()
                emit(ir.Copy(loc, var_right, var_result))
                emit(ir.Jump(loc, l_end))

                emit(l_skip)
                emit(ir.LoadBoolConst(loc, True, var_result))
                emit(ir.Jump(loc, l_end))

                emit(l_end)

                return var_result

            case ast.BinaryOp() if expr.op == "and":
                # Short-circuiting 'and' can be implemented using a conditional jump.
                l_right = new_label(expr.right.loc,'and_right')
                l_end = new_label(expr.right.loc, 'and_end')
                l_skip = new_label(expr.right.loc, 'and_skip')

                var_left = visit(st, expr.left)
                emit(ir.CondJump(loc, var_left, l_right, l_skip))

                emit(l_right)
                var_right = visit(st, expr.right)
                var_result = new_var()
                emit(ir.Copy(loc, var_right, var_result))
                emit(ir.Jump(loc, l_end))

                emit(l_skip)
                emit(ir.LoadBoolConst(loc, False, var_result))
                emit(l_end)

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
                emit(ir.Call(
                    loc, var_op, [var_left, var_right], var_result))
                return var_result

            case ast.IfThenElse():
                if expr.else_branch is None:
                    l_then = new_label(expr.then_branch.loc, 'then')
                    l_end = new_label(expr.loc, 'if_end')

                    var_cond = visit(st, expr.condition)
                    emit(ir.CondJump(loc, var_cond, l_then, l_end))

                    emit(l_then)
                    visit(st, expr.then_branch)

                    var_result = new_var()
                    emit(ir.Copy(loc, var_unit, var_result))

                    emit(l_end)

                    return var_result
                else:
                    # Similar to the above, but we also need to handle the "else" branch,
                    # and we need to generate a variable to hold the result of the whole expression.
                    l_then = new_label(expr.then_branch.loc, 'then')
                    l_else = new_label(expr.else_branch.loc, 'else')
                    l_end = new_label(expr.loc, 'if_end')

                    var_cond = visit(st, expr.condition)
                    emit(ir.CondJump(loc, var_cond, l_then, l_else))

                    var_result = new_var()

                    emit(l_then)
                    var_then = visit(st, expr.then_branch)
                    emit(ir.Copy(loc, var_then, var_result))
                    emit(ir.Jump(loc, l_end))

                    emit(l_else)
                    var_else = visit(st, expr.else_branch)
                    emit(ir.Copy(loc, var_else, var_result))

                    emit(l_end)

                    return var_result

            case ast.WhileExpr():
                l_start = new_label(expr.loc, 'while_start')
                emit(l_start)
                l_body = new_label(expr.body.loc, 'while_body')
                l_end = new_label(expr.loc, 'while_end')


                st.enter_loop(l_start, l_end)

                var_cond = visit(st, expr.condition)
                emit(ir.CondJump(loc, var_cond, l_body, l_end))

                emit(l_body)
                visit(st, expr.body)
                emit(ir.Jump(loc, l_start))
                emit(l_end)

                st.exit_loop()

                return var_unit

            case ast.FunctionExpr():
                var_fun = visit(st, expr.function_name)
                var_args = [visit(st, arg) for arg in expr.arguments]
                var_result = new_var()
                emit(ir.Call(loc, var_fun, var_args, var_result))
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
                emit(ir.Copy(loc, initializer_var, var_a))

                st.add_local(expr.name, var_a)

                return var_unit

            case ast.BreakExpr():
                if st.loop_end is None:
                    raise Exception(f"{loc}: 'break' outside of loop")
                emit(ir.Jump(loc, st.loop_end))
                return var_unit

            case ast.ContinueExpr():
                if st.loop_start is None:
                    raise Exception(f"{loc}: 'continue' outside of loop")
                emit(ir.Jump(loc, st.loop_start))
                return var_unit

            case ast.ReturnExpr():
                if expr.result is not None:
                    var_result = visit(st, expr.result)
                    emit(ir.Return(expr.loc, var_result))
                    return var_result
                else:
                    emit(ir.Return(expr.loc, var_unit_return))
                    return var_unit_return

            case ast.FunDefArgExpr():
                if isinstance(expr.name, ast.Identifier):
                    return st.require(expr.name.name)
                else:
                    return st.require(str(expr.name))

            case ast.FunDefExpr():
                if isinstance(expr.name, ast.Identifier):
                    func_name = expr.name.name

                old_function = current_function
                current_function = func_name
                in_function_def = True

                ins[func_name] = []

                param_names = []
                for param in expr.params:
                    if isinstance(param, ast.FunDefArgExpr):
                        if isinstance(param.name, ast.Identifier):
                            param_name = param.name.name
                            if param_name == 'x':
                                var_counter += 1
                            if param_name in param_names:
                                raise Exception("Function f has duplicate parameter names")
                            param_names.append(param.name.name)

                sig_label = ir.FunLabel(expr.loc, f"{func_name}({', '.join(param_names)})")
                emit(sig_label)

                param_vars = []
                param_names_list = []

                old_counter = var_counter

                for i, param in enumerate(expr.params):
                    if isinstance(param, ast.FunDefArgExpr):
                        if isinstance(param.name, ast.Identifier):
                            param_name = param.name.name

                        param_names_list.append(param_name)
                        param_var = ir.IRVar(param_name)
                        param_vars.append(param_var)

                func_st = SymTab(parent=st)

                for param_name, param_var in zip(param_names_list, param_vars):
                    func_st.add_local(param_name, param_var)

                visit(func_st, expr.body)

                has_return = any(isinstance(i, ir.Return) for i in ins[current_function])

                if not has_return:
                    emit(ir.Return(expr.loc, var_unit_return))

                for instruction in ins[current_function]:
                    if isinstance(instruction, ir.Return):
                        has_return = True
                        break

                func_var = ir.IRVar(func_name)
                st.add_local(func_name, func_var)

                var_counter = old_counter
                current_function = old_function

                return var_unit

            case ast.ModuleExpr():
                module_st = SymTab(parent=st)

                for item in expr.items:
                    if isinstance(item, ast.FunDefExpr):
                        if isinstance(item.name, ast.Identifier):
                            func_name = item.name.name
                        module_st.add_local(func_name, ir.IRVar(func_name))

                for item in expr.items:
                    if isinstance(item, ast.FunDefExpr):
                        visit(module_st, item)

                old_function = current_function
                current_function = "main"
                in_function_def = True
                ins["main"] = []

                main_label = ir.FunLabel(expr.loc, "main()")
                emit(main_label)

                last_var = var_unit
                for item in expr.items:
                    if isinstance(item, ast.FunctionExpr):
                        last_var = visit(module_st, item)

                current_function = old_function

                return last_var

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

    # visit(root_symtab, root_expr)

    # Start visiting the AST from the root.
    var_final_result = visit(root_symtab, root_expr)

    # Add IR code to print the result, based on the type assigned earlier by the type checker.
    if root_expr.type == Int:
        emit(ir.Call(
            root_expr.loc, ir.IRVar('print_int'), [var_final_result], new_var()))
    elif root_expr.type == Bool:
        emit(ir.Call(
            root_expr.loc, ir.IRVar('print_bool'), [var_final_result], new_var()))


    if in_function_def:
        emit(ir.Return(root_expr.loc, var_unit_return))

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
    with open('../test.src', 'r') as f:
        source = f.read()

    expr = parse(tokenize(source))

    env = setup_type_env()
    typecheck(expr, env)

    ins = generate_ir(reserved_names, expr)

    for fname, code in ins.items():
        for insn in code:
            print(insn)