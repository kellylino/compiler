import pytest
from compiler import ir
from compiler.ir import IRVar
from compiler.ir_generator import SymTab, generate_ir
from compiler.parser import parse
from compiler.tokenizer import tokenize
from compiler.type_checker import typecheck, setup_type_env

symtab: SymTab[IRVar] = SymTab()

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

def ir_from(src: str) -> list[ir.Instruction]:
    expr = parse(tokenize(src))
    env = setup_type_env()
    typecheck(expr, env)
    return generate_ir(reserved_names, expr)

def test_int_literal() -> None:
    ins = ir_from("1")

    assert isinstance(ins[0], ir.LoadIntConst)
    assert ins[0].value == 1

    assert isinstance(ins[-1], ir.Call)
    assert ins[-1].fun.name == "print_int"
    assert ins[-1].args == [ins[0].dest]

def test_bool_literal() -> None:
    ins = ir_from("true")

    assert isinstance(ins[0], ir.LoadBoolConst)
    assert ins[0].value is True

    assert isinstance(ins[1], ir.Call)
    assert ins[1].fun.name == "print_bool"
    assert ins[1].args == [ins[0].dest]

def test_identifier() -> None:
    ins = ir_from("var a = 1; a")

    assert isinstance(ins[0], ir.LoadIntConst)

    assert isinstance(ins[1], ir.Copy)
    a_var = ins[1].dest

    assert isinstance(ins[-1], ir.Call)
    assert ins[-1].fun.name == "print_int"
    assert ins[-1].args == [a_var]

def test_unary_minus() -> None:
    ins = ir_from("-1")

    assert isinstance(ins[0], ir.LoadIntConst)
    assert isinstance(ins[1], ir.Call)
    assert ins[1].fun.name == "unary_-"

    assert isinstance(ins[2], ir.Call)
    assert ins[2].fun.name == "print_int"
    assert ins[2].args == [ins[1].dest]

def test_unary_not() -> None:
    ins = ir_from("not true")

    assert isinstance(ins[0], ir.LoadBoolConst)
    assert ins[0].value is True

    assert isinstance(ins[1], ir.Call)
    assert ins[1].fun.name == "unary_not"

    assert isinstance(ins[2], ir.Call)
    assert ins[2].fun.name == "print_bool"
    assert ins[2].args == [ins[1].dest]

def test_binary_add() -> None:
    ins = ir_from("1 + 2")

    assert isinstance(ins[0], ir.LoadIntConst)
    assert isinstance(ins[1], ir.LoadIntConst)

    assert isinstance(ins[2], ir.Call)
    assert ins[2].fun.name == "+"
    assert ins[2].args == [ins[0].dest, ins[1].dest]

    assert isinstance(ins[3], ir.Call)
    assert ins[3].fun.name == "print_int"
    assert ins[3].args == [ins[2].dest]

def test_assignment() -> None:
    ins = ir_from("var a = 1; a = 2")
    assert isinstance(ins[0], ir.LoadIntConst)
    assert ins[0].value == 1
    assert isinstance(ins[1], ir.Copy)
    assert ins[1].source == ins[0].dest
    a_var = ins[1].dest

    assert isinstance(ins[2], ir.LoadIntConst)
    assert ins[2].value == 2
    assert isinstance(ins[3], ir.Copy)
    assert ins[3].source == ins[2].dest
    assert ins[3].dest == a_var

    assert isinstance(ins[4], ir.Call)
    assert ins[4].fun.name == "print_int"
    assert ins[4].args == [a_var]

def test_var_declaration() -> None:
    ins = ir_from("var a = 1")

    assert isinstance(ins[0], ir.LoadIntConst)
    assert isinstance(ins[1], ir.Copy)

def test_var_and_right_assignment() -> None:
    ins = ir_from("var a = 1; a = 3 + 1")

    assert isinstance(ins[0], ir.LoadIntConst)
    assert ins[0].value == 1

    assert isinstance(ins[1], ir.Copy)
    assert ins[1].source == ins[0].dest

    a_var = ins[1].dest

    assert isinstance(ins[2], ir.LoadIntConst)
    assert ins[2].value == 3

    assert isinstance(ins[3], ir.LoadIntConst)
    assert ins[3].value == 1

    assert isinstance(ins[4], ir.Call)
    assert ins[4].fun.name == "+"
    assert ins[4].args == [ins[2].dest, ins[3].dest]

    assert isinstance(ins[5], ir.Copy)
    assert ins[5].source == ins[4].dest
    assert ins[5].dest == a_var

    assert isinstance(ins[6], ir.Call)
    assert ins[6].fun.name == "print_int"
    assert ins[6].args == [a_var]

def test_or_expression() -> None:
    ins = ir_from("true or false")

    assert isinstance(ins[0], ir.LoadBoolConst)
    assert ins[0].value is True
    assert isinstance(ins[1], ir.CondJump)
    assert ins[1].cond == ins[0].dest
    assert ins[1].then_label.name == "or_skip"
    assert ins[1].else_label.name == "or_right"

    assert isinstance(ins[2], ir.Label)
    assert ins[2].name == "or_right"
    assert isinstance(ins[3], ir.LoadBoolConst)
    assert ins[3].value is False
    assert isinstance(ins[4], ir.Copy)
    assert ins[4].source == ins[3].dest
    assert isinstance(ins[5], ir.Jump)
    assert ins[5].label.name == "or_end"

    assert isinstance(ins[6], ir.Label)
    assert ins[6].name == "or_skip"
    assert isinstance(ins[7], ir.LoadBoolConst)
    assert ins[7].value is True
    assert isinstance(ins[8], ir.Jump)
    assert ins[8].label.name == "or_end"

    assert isinstance(ins[9], ir.Label)
    assert ins[9].name == "or_end"
    assert isinstance(ins[10], ir.Call)
    assert ins[10].fun.name == "print_bool"
    assert ins[10].args == [ins[4].dest]

def test_and_expression() -> None:
    ins = ir_from("true and false")

    assert any(isinstance(i, ir.CondJump) for i in ins)
    assert any(isinstance(i, ir.LoadBoolConst) and i.value is False for i in ins)

def test_if_then() -> None:
    ins = ir_from("if true then 1")

    assert any(isinstance(i, ir.CondJump) for i in ins)
    assert any(isinstance(i, ir.LoadIntConst) and i.value == 1 for i in ins)

def test_if_then_else() -> None:
    ins = ir_from("if true then 1 else 2")

    assert any(isinstance(i, ir.CondJump) for i in ins)

    copies = [i for i in ins if isinstance(i, ir.Copy)]
    assert len(copies) == 2

def test_while_loop() -> None:
    ins = ir_from("""
        var a = 0;
        while a < 3 do {
            a = a + 1;
        }
    """)

    assert any(isinstance(i, ir.Label) and "while_start" in i.name for i in ins)
    assert any(isinstance(i, ir.Jump) for i in ins)
    assert any(isinstance(i, ir.CondJump) for i in ins)

def test_function_call() -> None:
    ins = ir_from("print_int(1)")

    call = next(i for i in ins if isinstance(i, ir.Call))
    assert call.fun.name == "print_int"
    assert len(call.args) == 1

def test_block_expr() -> None:
    ins = ir_from("{ var a = 1; a + 2 }")

    assert any(isinstance(i, ir.Call) and i.fun.name == "+" for i in ins)
