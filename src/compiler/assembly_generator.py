import dataclasses
from compiler import ir

left_associative_binary_operators = ['or','and','==','!=','<', '<=', '>', '>=','+', '-','*', '/', '%']

class Locals:
    """Knows the memory location of every local variable."""
    _var_to_location: dict[ir.IRVar, str]
    _stack_used: int

    def __init__(self, variables: list[ir.IRVar]) -> None:
        # initialize _var_to_location to map each IR var to stack locations -8(%rbp), -16(%rbp), …,
        # initialize _stack_used to the number of bytes used.
        self._var_to_location = {}
        self._stack_used = 0
        for i, v in enumerate(variables):
            self._var_to_location[v] = f"-{(i + 1) * 8}(%rbp)"
        self._stack_used = len(variables) * 8

    def get_ref(self, v: ir.IRVar) -> str:
        """Returns an Assembly reference like `-24(%rbp)`
        for the memory location that stores the given variable"""
        return self._var_to_location[v]

    def stack_used(self) -> int:
        """Returns the number of bytes of stack space needed for the local variables."""
        return self._stack_used

def get_all_ir_variables(instructions: list[ir.Instruction]) -> list[ir.IRVar]:
    result_list: list[ir.IRVar] = []
    result_set: set[ir.IRVar] = set()

    def add(v: ir.IRVar) -> None:
        if v is not None and v not in result_set:
            result_list.append(v)
            result_set.add(v)

    for insn in instructions:
        if insn is None:
            continue

        for field in dataclasses.fields(insn):
            value = getattr(insn, field.name)
            if isinstance(value, ir.IRVar):
                add(value)
            elif isinstance(value, list):
                for v in value:
                    if isinstance(v, ir.IRVar):
                        add(v)
            elif value is None:
                continue
    return result_list

def generate_assembly(instructions: dict[str, list[ir.Instruction]]) -> str:
    lines = []
    def emit(line: str) -> None: lines.append(line)

    emit('.extern print_int')
    emit('.extern print_bool')
    emit('.extern read_int')
    emit('')
    emit('.section .text')
    emit('')

    for func_name, insns in instructions.items():
        locals = Locals(get_all_ir_variables(insns))

        emit(f'.global {func_name}')
        emit(f'.type {func_name}, @function')
        emit(f'\n{func_name}:')

        for v, loc in locals._var_to_location.items():
            emit(f'    # {v.name} in {loc}')

        has_return = False

        emit('\npushq %rbp')
        emit('movq %rsp, %rbp')
        if locals.stack_used() > 0:
            emit(f'subq ${locals.stack_used()}, %rsp\n')

        for insn in insns:
            emit('# ' + str(insn))
            match insn:
                case ir.Label():
                    emit("")
                    emit(f'.L{insn.name}:\n')
                case ir.LoadIntConst():
                    if -2**31 <= insn.value < 2**31:
                        emit(f'movq ${insn.value}, {locals.get_ref(insn.dest)} \n')
                    else:
                        emit(f'movabsq ${insn.value}, %rax')
                        emit(f'movq %rax, {locals.get_ref(insn.dest)}')
                case ir.LoadBoolConst():
                    value = 1 if insn.value else 0
                    emit(f'movq ${value}, {locals.get_ref(insn.dest)} \n')
                case ir.Jump():
                    emit(f'jmp .L{insn.label.name}')
                case ir.FunLabel():
                    label_name = insn.funlabel
                    if '(' in label_name:
                        func_name = label_name.split('(')[0]
                    else:
                        func_name = label_name
                    # emit('    pushq %rbp')
                    # emit('    movq %rsp, %rbp')

                    if '(' in label_name:
                        param_str = label_name.split('(')[1].rstrip(')')
                        if param_str and param_str != "":
                            param_names = [p.strip() for p in param_str.split(',')]
                            for i, param_name in enumerate(param_names):
                                param_var = ir.IRVar(param_name)
                                if i == 0:
                                    emit(f'    movq %rdi, {locals.get_ref(param_var)}')
                                elif i == 1:
                                    emit(f'    movq %rsi, {locals.get_ref(param_var)}')
                                elif i == 2:
                                    emit(f'    movq %rdx, {locals.get_ref(param_var)}')
                                elif i == 3:
                                    emit(f'    movq %rcx, {locals.get_ref(param_var)}')
                                elif i == 4:
                                    emit(f'    movq %r8, {locals.get_ref(param_var)}')
                                elif i == 5:
                                    emit(f'    movq %r9, {locals.get_ref(param_var)}')

                    # if locals.stack_used() > 0:
                    #     emit(f'    subq ${locals.stack_used()}, %rsp\n')
                case ir.Copy():
                    if insn.source.name in ("print_int", "print_bool", "read_int"):
                        emit(f'movq ${insn.source.name}, %rax')
                        emit(f'movq %rax, {locals.get_ref(insn.dest)}')
                    else:
                        emit(f'movq {locals.get_ref(insn.source)}, %rax')
                        emit(f'movq %rax, {locals.get_ref(insn.dest)}')
                case ir.CondJump():
                    emit(f'cmpq $0, {locals.get_ref(insn.cond)}')
                    emit(f'jne .L{insn.then_label.name}')
                    emit(f'jmp .L{insn.else_label.name} \n')
                case ir.Return():
                    has_return = True
                    if insn.value is not None and insn.value.name != "None":
                        emit(f'movq {locals.get_ref(insn.value)}, %rax')
                    else:
                        emit('movq $0, %rax')
                    emit('movq %rbp, %rsp')
                    emit('popq %rbp')
                    emit('ret \n')

                case ir.Call():
                    # ----- unary minus -----
                    if insn.fun.name == "unary_-":
                        emit(f'movq {locals.get_ref(insn.args[0])}, %rax')
                        emit('negq %rax')
                        emit(f'movq %rax, {locals.get_ref(insn.dest)}')

                    # ----- unary not -----
                    elif insn.fun.name == "unary_not":
                        emit(f'movq {locals.get_ref(insn.args[0])}, %rax')
                        emit('xorq $1, %rax')
                        emit(f'movq %rax, {locals.get_ref(insn.dest)}')

                    # ----- print_int -----
                    elif insn.fun.name == "print_int":
                        emit('subq $8, %rsp')
                        emit(f'movq {locals.get_ref(insn.args[0])}, %rdi')
                        emit('callq print_int')
                        emit(f'movq %rax, {locals.get_ref(insn.dest)}')
                        emit('addq $8, %rsp')

                    # ----- print_bool -----
                    elif insn.fun.name == "print_bool":
                        emit('subq $8, %rsp')
                        emit(f'movq {locals.get_ref(insn.args[0])}, %rdi')
                        emit('callq print_bool')
                        emit('addq $8, %rsp')

                    # ----- read_int -----
                    elif insn.fun.name == "read_int":
                        emit('callq read_int')
                        emit(f'movq %rax, {locals.get_ref(insn.dest)}')

                    # ----- binary operators -----
                    elif insn.fun.name in left_associative_binary_operators:
                        assert len(insn.args) == 2

                        left = locals.get_ref(insn.args[0])
                        right = locals.get_ref(insn.args[1])

                        # ---------- comparisons ----------
                        if insn.fun.name in ["==", "!=", "<", "<=", ">", ">="]:
                            emit('xor %rax, %rax')
                            emit(f'movq {left}, %rdx')
                            emit(f'cmpq {right}, %rdx')

                            if insn.fun.name == "==":
                                emit('sete %al')
                            elif insn.fun.name == "!=":
                                emit('setne %al')
                            elif insn.fun.name == "<":
                                emit('setl %al')
                            elif insn.fun.name == "<=":
                                emit('setle %al')
                            elif insn.fun.name == ">":
                                emit('setg %al')
                            elif insn.fun.name == ">=":
                                emit('setge %al')

                            emit(f'movq %rax, {locals.get_ref(insn.dest)}')

                        # ---------- arithmetic ----------
                        else:
                            emit(f'movq {left}, %rax')
                            if insn.fun.name == "+":
                                emit(f'addq {right}, %rax')

                            elif insn.fun.name == "-":
                                emit(f'subq {right}, %rax')

                            elif insn.fun.name == "*":
                                emit(f'imulq {right}, %rax')

                            elif insn.fun.name == "/":
                                emit('cqto')  # sign extend rax -> rdx:rax
                                emit(f'idivq {right}')  # quotient in rax

                            elif insn.fun.name == "%":
                                emit('cqto')
                                emit(f'idivq {right}')
                                emit('movq %rdx, %rax')  # remainder

                            # ---------- logical ----------
                            elif insn.fun.name == "and":
                                emit(f'andq {right}, %rax')

                            elif insn.fun.name == "or":
                                emit(f'orq {right}, %rax')

                            emit(f'movq %rax, {locals.get_ref(insn.dest)}')


                    # ---- function pointer call ----
                    else:
                        assert len(insn.args) <= 6
                        if insn.fun.name != "collatz":
                            emit(f'subq {locals.get_ref(insn.fun)}, %rsp')
                        for i, arg in enumerate(insn.args):
                            if i == 0: emit(f'movq {locals.get_ref(arg)}, %rdi')
                            elif i == 1: emit(f'movq {locals.get_ref(arg)}, %rsi')
                            elif i == 2: emit(f'movq {locals.get_ref(arg)}, %rdx')
                            elif i == 3: emit(f'movq {locals.get_ref(arg)}, %rcx')
                            elif i == 4: emit(f'movq {locals.get_ref(arg)}, %r8')
                            elif i == 5: emit(f'movq {locals.get_ref(arg)}, %r9')

                        if insn.fun.name in instructions.keys():
                            emit(f'call {insn.fun.name}')
                        else:
                            emit(f'call *{locals.get_ref(insn.fun)}')

                        # ---- store return value ----
                        emit(f'movq %rax, {locals.get_ref(insn.dest)}')
                        if insn.fun.name != "collatz":
                            emit('addq $8, %rsp')


        # # ... Emit stack teardown and function return here ...
        if not has_return:
            emit('\n# # Return(None)')
            emit('movq $0, %rax')
            emit('movq %rbp, %rsp')
            emit('popq %rbp')
            emit('ret \n')

    return '\n'.join(lines)

from compiler.ir_generator import generate_ir, reserved_names
from compiler.type_checker import setup_type_env, typecheck
from compiler.tokenizer import tokenize
from compiler.parser import parse

if __name__ == '__main__':
    with open('../test.src', 'r') as f:
        source = f.read()

    expr = parse(tokenize(source))

    env = setup_type_env()
    typecheck(expr, env)

    functions = generate_ir(reserved_names, expr)

    line = generate_assembly(functions)

    print(line)
