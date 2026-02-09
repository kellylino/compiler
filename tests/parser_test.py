from compiler.tokenizer import tokenize, L
from compiler.parser import parse
import compiler.ast as ast
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

# def VarExpr(name:ast.Expression, initializer:ast.Expression, typed: ast.Expression | None = None, function_type: ast.Expression | None = None) -> ast.VarExpr:
#     return ast.VarExpr(loc=L, name=name, typed=typed, initializer=initializer, function_type=function_type)

def VarExpr(name:str, initializer:ast.Expression, typed: ast.Expression | None = None) -> ast.VarExpr:
    return ast.VarExpr(loc=L, name=name, typed=typed, initializer=initializer)

def FunctionTypeExpr(return_type:ast.Expression, param_types:list[ast.Expression] | None = None) -> ast.FunctionTypeExpr:
    return ast.FunctionTypeExpr(loc=L, return_type=return_type, param_types=param_types)

# Task 1
def test_parser_basics() -> None:

    result = parse(tokenize('a + b'))
    assert result == BinaryOp(
        left=Identifier('a'),
        op='+',
        right=Identifier('b')
    )

def test_parser_associativity() -> None:

    result = parse(tokenize('1 - 2 + 3'))
    assert result == BinaryOp(
        left=BinaryOp(
            left=Literal(1),
            op='-',
            right=Literal(2)
        ),
        op='+',
        right=Literal(3),
    )

def test_parser_precedence() -> None:

    result = parse(tokenize('a + b * c'))
    assert result == BinaryOp(
        left=Identifier('a'),
        op='+',
        right=BinaryOp(
            left=Identifier('b'),
            op='*',
            right=Identifier('c')
        )
    )

def test_parser_parentheses() -> None:

    result = parse(tokenize('(a + b) * c'))
    assert result == BinaryOp(
        left=BinaryOp(
            left=Identifier('a'),
            op='+',
            right=Identifier('b')
        ),
        op='*',
        right=Identifier('c')
    )

def test_garbage_at_end() -> None:

    with pytest.raises(Exception, match="unexpected token"):
        parse(tokenize('a + b c'))

    with pytest.raises(Exception, match="unexpected token"):
        parse(tokenize('1 2'))

    with pytest.raises(Exception, match="unexpected token"):
        parse(tokenize('(a + b) x'))

    with pytest.raises(Exception, match="unexpected token"):
        parse(tokenize('a b'))

def test_empty_input() -> None:
    with pytest.raises(Exception, match="Empty input"):
        parse([])

# Task 2
def test_single_if_expression() -> None:

    result = parse(tokenize('if a then b + c'))
    assert result == IfThenElse(
        condition=Identifier('a'),
        then_branch=BinaryOp(
            left=Identifier('b'),
            op='+',
            right=Identifier('c')
        ),
        else_branch=None
    )

def test_single_if_else_expression() -> None:

    result = parse(tokenize('if a then b + c else x * y'))
    assert result == IfThenElse(
        condition=Identifier('a'),
        then_branch=BinaryOp(
            left=Identifier('b'),
            op='+',
            right=Identifier('c')
        ),
        else_branch=BinaryOp(
            left=Identifier('x'),
            op='*',
            right=Identifier('y')
        )
    )

def test_single_if_else_and_other_expression() -> None:

    result_1 = parse(tokenize('1 + if true then 2 else 3'))
    assert result_1 == BinaryOp(
        left=Literal(1),
        op='+',
        right=IfThenElse(
            condition=Identifier('true'),
            then_branch=Literal(2),
            else_branch=Literal(3)
        )
    )

    result_2 = parse(tokenize('a + b * c + if true then 2 else 3'))
    assert result_2 == BinaryOp(
        left=BinaryOp(
            left=Identifier('a'),
            op='+',
            right=BinaryOp(
                left=Identifier('b'),
                op='*',
                right=Identifier('c')
            )
        ),
        op='+',
        right=IfThenElse(
            condition=Identifier('true'),
            then_branch=Literal(2),
            else_branch=Literal(3)
        )
    )

    result_3 = parse(tokenize('a + b * if true then 2 else 3'))
    assert result_3 == BinaryOp(
        left=Identifier('a'),
        op='+',
        right=BinaryOp(
            left=Identifier('b'),
            op='*',
            right=IfThenElse(
                condition=Identifier('true'),
                then_branch=Literal(2),
                else_branch=Literal(3)
            )
        )
    )

def test_nested_if_else_expression() -> None:

    result = parse(tokenize('if a then b else if c then d else e'))
    assert result == IfThenElse(
        condition=Identifier('a'),
        then_branch=Identifier('b'),
        else_branch=IfThenElse(
            condition=Identifier('c'),
            then_branch=Identifier('d'),
            else_branch=Identifier('e')
        )
    )

def test_nested_if_else_and_other_expression() -> None:

    result_1 = parse(tokenize('1 + if true then 2 else if c then d else e'))
    assert result_1 == BinaryOp(
        left=Literal(1),
        op='+',
        right=IfThenElse(
            condition=Identifier('true'),
            then_branch=Literal(2),
            else_branch=IfThenElse(
                condition=Identifier('c'),
                then_branch=Identifier('d'),
                else_branch=Identifier('e')
            )
        )
    )

    result_2 = parse(tokenize('a + b * c + if true then 2 else if 1 then d else e'))
    assert result_2 == BinaryOp(
        left=BinaryOp(
            left=Identifier('a'),
            op='+',
            right=BinaryOp(
                left=Identifier('b'),
                op='*',
                right=Identifier('c')
            )
        ),
        op='+',
        right=IfThenElse(
            condition=Identifier('true'),
            then_branch=Literal(2),
            else_branch=IfThenElse(
                condition=Literal(1),
                then_branch=Identifier('d'),
                else_branch=Identifier('e')
            )
        )
    )

    result_3 = parse(tokenize('a + if b then c else d * if e then f else g'))
    assert result_3 == BinaryOp(
        left=Identifier('a'),
        op='+',
        right=IfThenElse(
            condition=Identifier('b'),
            then_branch=Identifier('c'),
            else_branch=BinaryOp(
                left=Identifier('d'),
                op='*',
                right=IfThenElse(
                    condition=Identifier('e'),
                    then_branch=Identifier('f'),
                    else_branch=Identifier('g')
                )
            )
        )
    )

# Task 3
def test_parser_function() -> None:

    result = parse(tokenize('f(x, y + z)'))
    assert result == FunctionExpr(
        function_name=Identifier('f'),
        arguments= [
            Identifier('x'),
            BinaryOp(
                left=Identifier('y'),
                op='+',
                right=Identifier('z')
            )
        ]
    )

def test_nested_parser_function() -> None:

    result = parse(tokenize('f(f(a))'))
    assert result == FunctionExpr(
        function_name=Identifier('f'),
        arguments=[
            FunctionExpr(
                function_name=Identifier('f'),
                arguments=[
                    Identifier('a')
                ]
            )
        ]
    )

def test_nested_parser_function_and_other() -> None:

    result = parse(tokenize('f(a * f(b)) + c'))
    assert result == BinaryOp(
        left=FunctionExpr(
            function_name=Identifier('f'),
            arguments=[
                BinaryOp(
                    left=Identifier('a'),
                    op='*',
                    right=FunctionExpr(
                        function_name=Identifier('f'),
                        arguments=[
                            Identifier('b'),
                        ]
                    )
                )
            ]
        ),
        op='+',
        right=Identifier('c')
    )

# Task 4
def test_right_parse_expression() -> None:

    result = parse(tokenize('a = b = c'))
    assert result == BinaryOp(
        left=Identifier('a'),
        op='=',
        right=BinaryOp(
            left=Identifier('b'),
            op='=',
            right=Identifier('c')
        )
    )

def test_left_associative_binary_operators() -> None:
    result_1 = parse(tokenize('a = b or c and d'))
    assert result_1 == BinaryOp(
        left=Identifier('a'),
        op='=',
        right=BinaryOp(
            left=Identifier('b'),
            op='or',
            right=BinaryOp(
                left=Identifier('c'),
                op='and',
                right=Identifier('d')
            )
        )
    )

    result_2 = parse(tokenize('a and b == c'))
    assert result_2 == BinaryOp(
        left=Identifier('a'),
        op='and',
        right=BinaryOp(
            left=Identifier('b'),
            op='==',
            right=Identifier('c')
        )
    )

    result_3 = parse(tokenize('a = b or c * 3 + 7 and d'))
    assert result_3 == BinaryOp(
        left=Identifier('a'),
        op='=',
        right=BinaryOp(
            left=Identifier('b'),
            op='or',
            right=BinaryOp(
                left=BinaryOp(
                    left=BinaryOp(
                        left=Identifier('c'),
                        op='*',
                        right=Literal(3)
                    ),
                    op='+',
                    right=Literal(7)
                ),
                op='and',
                right=Identifier('d')
            )
        )
    )

def test_unary_expression() -> None:
    result = parse(tokenize('not not x'))
    assert result == UnaryOp(
        op='not',
        operand=UnaryOp(
            op='not',
            operand=Identifier('x')
        )
    )

    result_2 = parse(tokenize('not not x + 3'))
    assert result_2 == BinaryOp(
        left=UnaryOp(
            op='not',
            operand=UnaryOp(
                op='not',
                operand=Identifier('x')
            )
        ),
        op='+',
        right=Literal(3)
    )

    result_3 = parse(tokenize('a = b or c * 3 > not -a + 3'))
    assert result_3 == BinaryOp(
        left=Identifier('a'),
        op='=',
        right=BinaryOp(
            left=Identifier('b'),
            op='or',
            right=BinaryOp(
                left=BinaryOp(
                    left=Identifier('c'),
                    op='*',
                    right=Literal(3)
                ),
                op='>',
                right=BinaryOp(
                    left=UnaryOp(
                    op='not',
                    operand=UnaryOp(
                        op='-',
                        operand=Identifier('a')
                        )
                    ),
                op='+',
                right=Literal(3)
                )
            )
        )
    )

    result_4 = parse(tokenize('-x'))
    assert result_4 == UnaryOp(
        op='-',
        operand=Identifier('x')
    )

def test_all_operator_precedence() -> None:

    result = parse(tokenize('not -a * b % 3 + c / 2 >= d - 1 == e != f and g < h or i'))
    assert result == BinaryOp(
        left=BinaryOp(
            left=BinaryOp(
                left=BinaryOp(
                    left=BinaryOp(
                        left=BinaryOp(
                            left=BinaryOp(
                                left=BinaryOp(
                                    left=UnaryOp(
                                        op='not',
                                        operand=UnaryOp(
                                            op='-',
                                            operand=Identifier('a')
                                        )
                                    ),
                                    op='*',
                                    right=Identifier('b')
                                ),
                                op='%',
                                right=Literal(3)
                            ),
                            op='+',
                            right=BinaryOp(
                                left=Identifier('c'),
                                op='/',
                                right=Literal(2)
                            )
                        ),
                        op='>=',
                        right=BinaryOp(
                            left=Identifier('d'),
                            op='-',
                            right=Literal(1)
                        )
                    ),
                    op='==',
                    right=Identifier('e')
                ),
                op='!=',
                right=Identifier('f')
                ),
            op='and',
            right=BinaryOp(
                left=Identifier('g'),
                op='<',
                right=Identifier('h')
            )
        ),
        op='or',
        right=Identifier('i')
    )

# Task 5
def test_block_expression() -> None:
    result = parse(tokenize('{f(a); x = y; f(x)}'))
    assert result == BlockExpr(
        statements=[
            FunctionExpr(
                function_name=Identifier('f'),
                arguments=[
                    Identifier('a')
                ]
            ),
            BinaryOp(
                left=Identifier('x'),
                op='=',
                right=Identifier('y')
            ),
            FunctionExpr(
                function_name=Identifier('f'),
                arguments=[
                    Identifier('x')
                ]
            )
        ]
    )

def test_block_value() -> None:
    result = parse(tokenize('x = { f(a); b }'))
    assert result == BinaryOp(
        left=Identifier('x'),
        op='=',
        right=BlockExpr(
            statements=[
                FunctionExpr(
                    function_name=Identifier('f'),
                    arguments=[
                        Identifier('a')
                    ]
                ),
                Identifier('b')
            ]
        )
    )

def test_while_expression() -> None:
    result = parse(tokenize('while a + b = c do 1'))
    assert result ==WhileExpr(
        condition=BinaryOp(
            left=BinaryOp(
                left=Identifier('a'),
                op='+',
                right=Identifier('b')
            ),
            op='=',
            right=Identifier('c')
        ),
        body=Literal(1)
    )

def test_complex_block_expression() -> None:

    result = parse(tokenize("""
    {
        while f() do {
            x = 10;
            y = if g(x) then {
                x = x + 1;
                x
            } else {
                g(x)
            }
            g(y);
        }
        123
    }
    """))
    assert result == BlockExpr(
        statements=[
           WhileExpr(
                condition=FunctionExpr(
                    function_name=Identifier('f'),
                    arguments=[]
                ),
                body=BlockExpr(
                    statements=[
                        BinaryOp(
                            left=Identifier('x'),
                            op='=',
                            right=Literal(10)
                        ),
                        BinaryOp(
                            left=Identifier('y'),
                            op='=',
                            right=IfThenElse(
                                condition=FunctionExpr(
                                    function_name=Identifier('g'),
                                    arguments=[
                                        Identifier('x')
                                    ]
                                ),
                                then_branch=BlockExpr(
                                    statements=[
                                        BinaryOp(
                                            left=Identifier('x'),
                                            op='=',
                                            right=BinaryOp(
                                                left=Identifier('x'),
                                                op='+',
                                                right=Literal(1)
                                            )
                                        ),
                                        Identifier('x')
                                    ]
                                ),
                                else_branch=BlockExpr(
                                    statements=[
                                        FunctionExpr(
                                            function_name=Identifier('g'),
                                            arguments=[
                                                Identifier('x')
                                            ]
                                        )
                                    ]
                                )
                            )
                        ),
                        FunctionExpr(
                            function_name=Identifier('g'),
                            arguments=[
                                Identifier('y')
                            ]
                        ),
                        Identifier('Unit')
                    ]
                )
            ),
            Literal(123)
        ]
    )

# Task 6
def test_var_expression() -> None:
    result = parse(tokenize('var x = 3'))
    assert result == VarExpr(
        name='x',
        typed=None,
        initializer=Literal(3)
    )

    result_2 = parse(tokenize('{var x = 3}'))
    assert result_2 == BlockExpr(
       statements=[
           VarExpr(
            name='x',
            typed=None,
            initializer=Literal(3)
           )
       ]
    )

    result_3 = parse(tokenize('{f(a); var x = 8; f(x)}'))
    assert result_3 == BlockExpr(
        statements=[
            FunctionExpr(
                function_name=Identifier('f'),
                arguments=[
                    Identifier('a')
                ]
            ),
            VarExpr(
                name='x',
                typed=None,
                initializer=Literal(8)
            ),
            FunctionExpr(
                function_name=Identifier('f'),
                arguments=[
                    Identifier('x')
                ]
            )
        ]
    )

    result = parse(tokenize('var ID: T = E'))
    assert result == VarExpr(
        name='ID',
        typed=Identifier('T'),
        initializer=Identifier('E'),
    )

def test_var_expression_in_other_lever() -> None:
    with pytest.raises(Exception, match="unexpected token var"):
        parse(tokenize('f(var = a)'))

    with pytest.raises(Exception, match="unexpected token var"):
        parse(tokenize('if 8 then var x = 3'))

    with pytest.raises(Exception, match="unexpected token var"):
        parse(tokenize('if var x = 3 then a'))

    with pytest.raises(Exception, match="unexpected token var"):
        parse(tokenize('if b = 6 then a else var c = 8'))

    with pytest.raises(Exception, match="unexpected token var"):
        parse(tokenize('while var b = 3 do c'))

    with pytest.raises(Exception, match="unexpected token var"):
        parse(tokenize('while true do var a = 9'))

# Task 7
def test_more_block_expression() -> None:

    result = parse(tokenize('{ { a } { b } }'))
    assert result == BlockExpr(
        statements=[
            BlockExpr(
                statements=[
                    Identifier('a')
                ]
            ),
            BlockExpr(
                statements=[
                    Identifier('b')
                ]
            )
        ]
    )

    with pytest.raises(Exception, match= 'expected token "}" or ";"'):
        parse(tokenize('{ a b }'))

    result = parse(tokenize('{ if true then { a } b }'))
    assert result == BlockExpr(
        statements=[
            IfThenElse(
                condition=Identifier('true'),
                then_branch=BlockExpr(
                    statements=[
                        Identifier('a')
                    ]
                ),
                else_branch=None
            ),
            Identifier('b')
        ]
    )

    result = parse(tokenize('{ if true then { a }; b }'))
    assert result == BlockExpr(
        statements=[
            IfThenElse(
                condition=Identifier('true'),
                then_branch=BlockExpr(
                    statements=[
                        Identifier('a')
                    ]
                ),
                else_branch=None
            ),
            Identifier('b')
        ]
    )

    with pytest.raises(Exception, match= 'expected token "}" or ";"'):
        parse(tokenize('{ if true then { a } b c }'))

    result = parse(tokenize('{ if true then { a }; b; c }'))
    assert result == BlockExpr(
        statements=[
            IfThenElse(
                condition=Identifier('true'),
                then_branch=BlockExpr(
                    statements=[
                        Identifier('a')
                    ]
                ),
                else_branch=None
            ),
            Identifier('b'),
            Identifier('c')
        ]
    )

    result = parse(tokenize('{ if true then { a } else { b } c }'))
    assert result == BlockExpr(
        statements=[
            IfThenElse(
                condition=Identifier('true'),
                then_branch=BlockExpr(
                    statements=[
                        Identifier('a')
                    ]
                ),
                else_branch=BlockExpr(
                    statements=[
                        Identifier('b')
                    ]
                )
            ),
            Identifier('c')
        ]
    )

    result = parse(tokenize('x = { { f(a) } { b } }'))
    assert result == BinaryOp(
        left=Identifier('x'),
        op='=',
        right=BlockExpr(
            statements=[
                BlockExpr(
                    statements=[
                        FunctionExpr(
                            function_name=Identifier('f'),
                            arguments=[
                                Identifier('a')
                            ]
                        )
                    ]
                ),
                BlockExpr(
                    statements=[
                        Identifier('b')
                    ]
                )
            ]
        )
    )

# Task 8
# After add loc arg, add helper function to make tests less verbose

# Task 9
def test_multiple_top_level_expressions() -> None:

    result = parse(tokenize('a = 1; b = 2; a + b'))
    assert result == BlockExpr(
        statements=[
            BinaryOp(
                left=Identifier('a'),
                op='=',
                right=Literal(1)
            ),
            BinaryOp(
                left=Identifier('b'),
                op='=',
                right=Literal(2)
            ),
            BinaryOp(
                left=Identifier('a'),
                op='+',
                right=Identifier('b')
            )
        ]
)

def test_syntax_example() -> None:

    result = parse(tokenize("""
        var n: Int = read_int();
        print_int(n);
        while n > 1 do {
            if n % 2 == 0 then {
                n = n / 2;
            } else {
                n = 3 * n + 1;
            }
            print_int(n);
        }
    """))

    assert result == BlockExpr(
        statements=[
            VarExpr(
                name='n',
                typed=Identifier('Int'),
                initializer=FunctionExpr(
                    function_name=Identifier('read_int'),
                    arguments=[]
                )
            ),
            FunctionExpr(
                function_name=Identifier('print_int'),
                arguments=[Identifier('n')]
            ),
            WhileExpr(
                condition=BinaryOp(
                    left=Identifier('n'),
                    op='>',
                    right=Literal(1)
                ),
                body=BlockExpr(
                    statements=[
                        IfThenElse(
                            condition=BinaryOp(
                                left=BinaryOp(
                                    left=Identifier('n'),
                                    op='%',
                                    right=Literal(2)
                                ),
                                op='==',
                                right=Literal(0)
                            ),
                            then_branch=BlockExpr(
                                statements=[
                                    BinaryOp(
                                        left=Identifier('n'),
                                        op='=',
                                        right=BinaryOp(
                                            left=Identifier('n'),
                                            op='/',
                                            right=Literal(2)
                                        )
                                    ),
                                    Identifier('Unit')
                                ]
                            ),
                            else_branch=BlockExpr(
                                statements=[
                                    BinaryOp(
                                        left=Identifier('n'),
                                        op='=',
                                        right=BinaryOp(
                                            left=BinaryOp(
                                                left=Literal(3),
                                                op='*',
                                                right=Identifier('n')
                                            ),
                                            op='+',
                                            right=Literal(1)
                                        )
                                    ),
                                    Identifier('Unit')
                                ]
                            )
                        ),
                        FunctionExpr(
                            function_name=Identifier('print_int'),
                            arguments=[Identifier('n')]
                        ),
                        Identifier('Unit')
                    ]
                )
            )
        ]
    )

def test_var_function_type_expression() -> None:
    result = parse(tokenize('{ var f: (Int) => Unit = print_int; f(123) }'))

    assert result == BlockExpr(
        statements=[
            VarExpr(
                name='f',
                typed=FunctionTypeExpr(
                    return_type=Identifier('Unit'),
                    param_types=[Identifier('Int')]
                ),
                initializer=Identifier('print_int')
            ),
            FunctionExpr(
                function_name=Identifier('f'),
                arguments=[
                    Literal(123)
                ]
            )
        ]
    )

def test_var_function_type_expression_no_param() -> None:
    result = parse(tokenize('{ var f: () => Unit = print_int; f() }'))

    assert result == BlockExpr(
        statements=[
            VarExpr(
                name='f',
                typed=FunctionTypeExpr(
                    return_type=Identifier('Unit'),
                    param_types=None
                ),
                initializer=Identifier('print_int')
            ),
            FunctionExpr(
                function_name=Identifier('f'),
                arguments=[]
            )
        ]
    )

def test_var_with_semicolon_end() -> None:
    result = parse(tokenize('var x = 3;'))

    assert result == BlockExpr(
        statements=[
            VarExpr(
                name='x',
                typed=None,
                initializer=Literal(3)
            ),
            Identifier('Unit')
        ]
    )