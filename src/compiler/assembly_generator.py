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
        if v not in result_set:
            result_list.append(v)
            result_set.add(v)

    for insn in instructions:
        for field in dataclasses.fields(insn):
            value = getattr(insn, field.name)
            if isinstance(value, ir.IRVar):
                add(value)
            elif isinstance(value, list):
                for v in value:
                    if isinstance(v, ir.IRVar):
                        add(v)
    return result_list

def generate_assembly(instructions: list[ir.Instruction]) -> str:
    lines = []
    def emit(line: str) -> None: lines.append(line)

    locals = Locals(
        variables=get_all_ir_variables(instructions)
    )

    # ... Emit initial declarations and stack setup here ...
    emit('.extern print_int')
    emit('.extern print_bool')
    emit('.extern read_int \n')

    emit('.section .text\n')

    emit('.global main')
    emit('.type main, @function \n')

    emit('main:')

    for v, loc in locals._var_to_location.items():
        emit(f'    # {v.name} in {loc}')


    emit('\npushq %rbp')
    emit('movq %rsp, %rbp')
    if locals.stack_used() > 0:
        emit(f'subq ${locals.stack_used()}, %rsp\n')


    for insn in instructions:
        emit('# ' + str(insn))
        match insn:
            case ir.Label():
                emit("")
                # ".L" prefix marks the symbol as "private".
                # This makes GDB backtraces look nicer too:
                # https://stackoverflow.com/a/26065570/965979
                emit(f'.L{insn.name}:\n')
            case ir.LoadIntConst():
                if -2**31 <= insn.value < 2**31:
                    emit(f'movq ${insn.value}, {locals.get_ref(insn.dest)} \n')
                else:
                    # Due to a quirk of x86-64, we must use
                    # a different instruction for large integers.
                    # It can only write to a register,
                    # not a memory location, so we use %rax
                    # as a temporary.
                    emit(f'movabsq ${insn.value}, %rax')
                    emit(f'movq %rax, {locals.get_ref(insn.dest)}')
            case ir.LoadBoolConst():
                value = 1 if insn.value else 0
                emit(f'movq ${value}, {locals.get_ref(insn.dest)} \n')
            case ir.Jump():
                emit(f'jmp .L{insn.label.name}')
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
            case ir.Call():
                assert len(insn.args) <= 6
                for i, arg in enumerate(insn.args):
                    if i == 0: emit(f'movq {locals.get_ref(arg)}, %rdi')
                    elif i == 1: emit(f'movq {locals.get_ref(arg)}, %rsi')
                    elif i == 2: emit(f'movq {locals.get_ref(arg)}, %rdx')
                    elif i == 3: emit(f'movq {locals.get_ref(arg)}, %rcx')
                    elif i == 4: emit(f'movq {locals.get_ref(arg)}, %r8')
                    elif i == 5: emit(f'movq {locals.get_ref(arg)}, %r9')

                # ----- unary minus -----
                if insn.fun.name == "unary_-":
                    emit(f'movq {locals.get_ref(insn.args[0])}, %rax')
                    emit('negq %rax')

                # ----- unary not -----
                elif insn.fun.name == "unary_not":
                    emit(f'movq {locals.get_ref(insn.args[0])}, %rax')
                    emit('xorq $1, %rax')

                # ----- print_int -----
                elif insn.fun.name == "print_int":
                    emit(f'movq {locals.get_ref(insn.args[0])}, %rdi')
                    emit('callq print_int')

                # ----- print_bool -----
                elif insn.fun.name == "print_bool":
                    emit('subq $8, %rsp')
                    emit(f'movq {locals.get_ref(insn.args[0])}, %rdi')
                    emit('callq print_bool')
                    emit('addq $8, %rsp')

                # ----- read_int -----
                elif insn.fun.name == "read_int":
                    emit('subq $8, %rsp')
                    emit('callq read_int')
                    emit('addq $8, %rsp')

                # ----- binary operators -----
                elif insn.fun.name in left_associative_binary_operators:
                    assert len(insn.args) == 2

                    left = locals.get_ref(insn.args[0])
                    right = locals.get_ref(insn.args[1])

                    # Load left operand into %rax
                    emit(f'movq {left}, %rax')

                    # ---------- arithmetic ----------
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

                    # ---------- comparisons ----------
                    elif insn.fun.name in ["==", "!=", "<", "<=", ">", ">="]:
                        emit(f'cmpq {right}, %rax')

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

                        emit('movzbq %al, %rax')

                    # ---------- logical ----------
                    elif insn.fun.name == "and":
                        emit(f'andq {right}, %rax')

                    elif insn.fun.name == "or":
                        emit(f'orq {right}, %rax')


                # ---- function pointer call ----
                else:
                    emit(f'movq {locals.get_ref(insn.fun)}, %rax')
                    emit('call *%rax')

                # ---- store return value ----
                emit(f'movq %rax, {locals.get_ref(insn.dest)}')


    # ... Emit stack teardown and function return here ...
    emit('# # Return(None)')
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

    expr = parse(tokenize("""var x = print_int;
                x(4)
                """))

    env = setup_type_env()
    typecheck(expr, env)

    ins = generate_ir(reserved_names, expr)

    line = generate_assembly(ins)

    print(line)
