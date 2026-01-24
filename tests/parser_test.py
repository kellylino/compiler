from compiler.tokenizer import tokenize
from compiler.parser import parse
import compiler.ast as ast
import pytest

# Task 1
def test_parser_basics() -> None:

    result = parse(tokenize('a + b'))
    assert result == ast.BinaryOp(
        left=ast.Identifier('a'),
        op='+',
        right=ast.Identifier('b')
    )

def test_parser_associativity() -> None:

    result = parse(tokenize('1 - 2 + 3'))
    assert result == ast.BinaryOp(
        left=ast.BinaryOp(
            left=ast.Literal(1),
            op='-',
            right=ast.Literal(2)
        ),
        op='+',
        right=ast.Literal(3),
    )

def test_parser_precedence() -> None:

    result = parse(tokenize('a + b * c'))
    assert result == ast.BinaryOp(
        left=ast.Identifier('a'),
        op='+',
        right=ast.BinaryOp(
            left=ast.Identifier('b'),
            op='*',
            right=ast.Identifier('c')
        )
    )

def test_parser_parentheses() -> None:

    result = parse(tokenize('(a + b) * c'))
    assert result == ast.BinaryOp(
        left=ast.BinaryOp(
            left=ast.Identifier('a'),
            op='+',
            right=ast.Identifier('b')
        ),
        op='*',
        right=ast.Identifier('c')
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
    assert result == ast.IfExpr(
        condition=ast.Identifier('a'),
        then_branch=ast.BinaryOp(
            left=ast.Identifier('b'),
            op='+',
            right=ast.Identifier('c')
        ),
        else_branch=None
    )

def test_single_if_else_expression() -> None:

    result = parse(tokenize('if a then b + c else x * y'))
    assert result == ast.IfExpr(
        condition=ast.Identifier('a'),
        then_branch=ast.BinaryOp(
            left=ast.Identifier('b'),
            op='+',
            right=ast.Identifier('c')
        ),
        else_branch=ast.BinaryOp(
            left=ast.Identifier('x'),
            op='*',
            right=ast.Identifier('y')
        )
    )

def test_single_if_else_and_other_expression() -> None:

    result_1 = parse(tokenize('1 + if true then 2 else 3'))
    assert result_1 == ast.BinaryOp(
        left=ast.Literal(1),
        op='+',
        right=ast.IfExpr(
            condition=ast.Identifier('true'),
            then_branch=ast.Literal(2),
            else_branch=ast.Literal(3)
        )
    )

    result_2 = parse(tokenize('a + b * c + if true then 2 else 3'))
    assert result_2 == ast.BinaryOp(
        left=ast.BinaryOp(
            left=ast.Identifier('a'),
            op='+',
            right=ast.BinaryOp(
                left=ast.Identifier('b'),
                op='*',
                right=ast.Identifier('c')
            )
        ),
        op='+',
        right=ast.IfExpr(
            condition=ast.Identifier('true'),
            then_branch=ast.Literal(2),
            else_branch=ast.Literal(3)
        )
    )

    result_3 = parse(tokenize('a + b * if true then 2 else 3'))
    assert result_3 == ast.BinaryOp(
        left=ast.Identifier('a'),
        op='+',
        right=ast.BinaryOp(
            left=ast.Identifier('b'),
            op='*',
            right=ast.IfExpr(
                condition=ast.Identifier('true'),
                then_branch=ast.Literal(2),
                else_branch=ast.Literal(3)
            )
        )
    )

def test_nested_if_else_expression() -> None:

    result = parse(tokenize('if a then b else if c then d else e'))
    assert result == ast.IfExpr(
        condition=ast.Identifier('a'),
        then_branch=ast.Identifier('b'),
        else_branch=ast.IfExpr(
            condition=ast.Identifier('c'),
            then_branch=ast.Identifier('d'),
            else_branch=ast.Identifier('e')
        )
    )

def test_nested_if_else_and_other_expression() -> None:

    result_1 = parse(tokenize('1 + if true then 2 else if c then d else e'))
    assert result_1 == ast.BinaryOp(
        left=ast.Literal(1),
        op='+',
        right=ast.IfExpr(
            condition=ast.Identifier('true'),
            then_branch=ast.Literal(2),
            else_branch=ast.IfExpr(
                condition=ast.Identifier('c'),
                then_branch=ast.Identifier('d'),
                else_branch=ast.Identifier('e')
            )
        )
    )

    result_2 = parse(tokenize('a + b * c + if true then 2 else if 1 then d else e'))
    assert result_2 == ast.BinaryOp(
        left=ast.BinaryOp(
            left=ast.Identifier('a'),
            op='+',
            right=ast.BinaryOp(
                left=ast.Identifier('b'),
                op='*',
                right=ast.Identifier('c')
            )
        ),
        op='+',
        right=ast.IfExpr(
            condition=ast.Identifier('true'),
            then_branch=ast.Literal(2),
            else_branch=ast.IfExpr(
                condition=ast.Literal(1),
                then_branch=ast.Identifier('d'),
                else_branch=ast.Identifier('e')
            )
        )
    )

    result_3 = parse(tokenize('a + if b then c else d * if e then f else g'))
    assert result_3 == ast.BinaryOp(
        left=ast.Identifier('a'),
        op='+',
        right=ast.IfExpr(
            condition=ast.Identifier('b'),
            then_branch=ast.Identifier('c'),
            else_branch=ast.BinaryOp(
                left=ast.Identifier('d'),
                op='*',
                right=ast.IfExpr(
                    condition=ast.Identifier('e'),
                    then_branch=ast.Identifier('f'),
                    else_branch=ast.Identifier('g')
                )
            )
        )
    )

# Task 3
def test_parser_function() -> None:

    result = parse(tokenize('f(x, y + z)'))
    assert result == ast.FunctionExpr(
        function_name=ast.Identifier('f'),
        arguments= [
            ast.Identifier('x'),
            ast.BinaryOp(
                left=ast.Identifier('y'),
                op='+',
                right=ast.Identifier('z')
            )
        ]
    )

def test_nested_parser_function() -> None:

    result = parse(tokenize('f(f(a))'))
    assert result == ast.FunctionExpr(
        function_name=ast.Identifier('f'),
        arguments=[
            ast.FunctionExpr(
                function_name=ast.Identifier('f'),
                arguments=[
                    ast.Identifier('a')
                ]
            )
        ]
    )

def test_nested_parser_function_and_other() -> None:

    result = parse(tokenize('f(a * f(b)) + c'))
    assert result == ast.BinaryOp(
        left=ast.FunctionExpr(
            function_name=ast.Identifier('f'),
            arguments=[
                ast.BinaryOp(
                    left=ast.Identifier('a'),
                    op='*',
                    right=ast.FunctionExpr(
                        function_name=ast.Identifier('f'),
                        arguments=[
                            ast.Identifier('b'),
                        ]
                    )
                )
            ]
        ),
        op='+',
        right=ast.Identifier('c')
    )

# Task 4
def test_right_parse_expression() -> None:

    result = parse(tokenize('a = b = c'))
    assert result == ast.BinaryOp(
        left=ast.Identifier('a'),
        op='=',
        right=ast.BinaryOp(
            left=ast.Identifier('b'),
            op='=',
            right=ast.Identifier('c')
        )
    )

def test_left_associative_binary_operators() -> None:
    result_1 = parse(tokenize('a = b or c and d'))
    assert result_1 == ast.BinaryOp(
        left=ast.Identifier('a'),
        op='=',
        right=ast.BinaryOp(
            left=ast.Identifier('b'),
            op='or',
            right=ast.BinaryOp(
                left=ast.Identifier('c'),
                op='and',
                right=ast.Identifier('d')
            )
        )
    )

    result_2 = parse(tokenize('a and b == c'))
    assert result_2 == ast.BinaryOp(
        left=ast.Identifier('a'),
        op='and',
        right=ast.BinaryOp(
            left=ast.Identifier('b'),
            op='==',
            right=ast.Identifier('c')
        )
    )

    result_3 = parse(tokenize('a = b or c * 3 + 7 and d'))
    assert result_3 == ast.BinaryOp(
        left=ast.Identifier('a'),
        op='=',
        right=ast.BinaryOp(
            left=ast.Identifier('b'),
            op='or',
            right=ast.BinaryOp(
                left=ast.BinaryOp(
                    left=ast.BinaryOp(
                        left=ast.Identifier('c'),
                        op='*',
                        right=ast.Literal(3)
                    ),
                    op='+',
                    right=ast.Literal(7)
                ),
                op='and',
                right=ast.Identifier('d')
            )
        )
    )

def test_unary_expression() -> None:
    result = parse(tokenize('not not x'))
    assert result == ast.UnaryOp(
        op='not',
        operand=ast.UnaryOp(
            op='not',
            operand=ast.Identifier('x')
        )
    )

    result_2 = parse(tokenize('not not x + 3'))
    assert result_2 == ast.BinaryOp(
        left=ast.UnaryOp(
            op='not',
            operand=ast.UnaryOp(
                op='not',
                operand=ast.Identifier('x')
            )
        ),
        op='+',
        right=ast.Literal(3)
    )

    result_3 = parse(tokenize('a = b or c * 3 > not -a + 3'))
    assert result_3 == ast.BinaryOp(
        left=ast.Identifier('a'),
        op='=',
        right=ast.BinaryOp(
            left=ast.Identifier('b'),
            op='or',
            right=ast.BinaryOp(
                left=ast.BinaryOp(
                    left=ast.Identifier('c'),
                    op='*',
                    right=ast.Literal(3)
                ),
                op='>',
                right=ast.BinaryOp(
                    left=ast.UnaryOp(
                    op='not',
                    operand=ast.UnaryOp(
                        op='-',
                        operand=ast.Identifier('a')
                        )
                    ),
                op='+',
                right=ast.Literal(3)
                )
            )
        )
    )

    result_4 = parse(tokenize('-x'))
    assert result_4 == ast.UnaryOp(
        op='-',
        operand=ast.Identifier('x')
    )

def test_all_operator_precedence() -> None:

    result = parse(tokenize('not -a * b % 3 + c / 2 >= d - 1 == e != f and g < h or i'))
    assert result == ast.BinaryOp(
        left=ast.BinaryOp(
            left=ast.BinaryOp(
                left=ast.BinaryOp(
                    left=ast.BinaryOp(
                        left=ast.BinaryOp(
                            left=ast.BinaryOp(
                                left=ast.BinaryOp(
                                    left=ast.UnaryOp(
                                        op='not',
                                        operand=ast.UnaryOp(
                                            op='-',
                                            operand=ast.Identifier('a')
                                        )
                                    ),
                                    op='*',
                                    right=ast.Identifier('b')
                                ),
                                op='%',
                                right=ast.Literal(3)
                            ),
                            op='+',
                            right=ast.BinaryOp(
                                left=ast.Identifier('c'),
                                op='/',
                                right=ast.Literal(2)
                            )
                        ),
                        op='>=',
                        right=ast.BinaryOp(
                            left=ast.Identifier('d'),
                            op='-',
                            right=ast.Literal(1)
                        )
                    ),
                    op='==',
                    right=ast.Identifier('e')
                ),
                op='!=',
                right=ast.Identifier('f')
                ),
            op='and',
            right=ast.BinaryOp(
                left=ast.Identifier('g'),
                op='<',
                right=ast.Identifier('h')
            )
        ),
        op='or',
        right=ast.Identifier('i')
    )

# Task 5
def test_block_expression() -> None:
    result = parse(tokenize('{f(a); x = y; f(x)}'))
    assert result == ast.BlockExpr(
        statements=[
            ast.FunctionExpr(
                function_name=ast.Identifier('f'),
                arguments=[
                    ast.Identifier('a')
                ]
            ),
            ast.BinaryOp(
                left=ast.Identifier('x'),
                op='=',
                right=ast.Identifier('y')
            ),
            ast.FunctionExpr(
                function_name=ast.Identifier('f'),
                arguments=[
                    ast.Identifier('x')
                ]
            )
        ]
    )

def test_block_value() -> None:
    result = parse(tokenize('x = { f(a); b }'))
    assert result == ast.BinaryOp(
        left=ast.Identifier('x'),
        op='=',
        right=ast.BlockExpr(
            statements=[
                ast.FunctionExpr(
                    function_name=ast.Identifier('f'),
                    arguments=[
                        ast.Identifier('a')
                    ]
                ),
                ast.Identifier('b')
            ]
        )
    )

def test_while_expression() -> None:
    result = parse(tokenize('while a + b = c do 1'))
    assert result == ast.WhileExpr(
        condition=ast.BinaryOp(
            left=ast.BinaryOp(
                left=ast.Identifier('a'),
                op='+',
                right=ast.Identifier('b')
            ),
            op='=',
            right=ast.Identifier('c')
        ),
        body=ast.Literal(1)
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
    assert result == ast.BlockExpr(
        statements=[
            ast.WhileExpr(
                condition=ast.FunctionExpr(
                    function_name=ast.Identifier('f'),
                    arguments=[]
                ),
                body=ast.BlockExpr(
                    statements=[
                        ast.BinaryOp(
                            left=ast.Identifier('x'),
                            op='=',
                            right=ast.Literal(10)
                        ),
                        ast.BinaryOp(
                            left=ast.Identifier('y'),
                            op='=',
                            right=ast.IfExpr(
                                condition=ast.FunctionExpr(
                                    function_name=ast.Identifier('g'),
                                    arguments=[
                                        ast.Identifier('x')
                                    ]
                                ),
                                then_branch=ast.BlockExpr(
                                    statements=[
                                        ast.BinaryOp(
                                            left=ast.Identifier('x'),
                                            op='=',
                                            right=ast.BinaryOp(
                                                left=ast.Identifier('x'),
                                                op='+',
                                                right=ast.Literal(1)
                                            )
                                        ),
                                        ast.Identifier('x')
                                    ]
                                ),
                                else_branch=ast.BlockExpr(
                                    statements=[
                                        ast.FunctionExpr(
                                            function_name=ast.Identifier('g'),
                                            arguments=[
                                                ast.Identifier('x')
                                            ]
                                        )
                                    ]
                                )
                            )
                        ),
                        ast.FunctionExpr(
                            function_name=ast.Identifier('g'),
                            arguments=[
                                ast.Identifier('y')
                            ]
                        )
                    ]
                )
            ),
            ast.Literal(123)
        ]
    )

# Task 6
def test_var_expression() -> None:
    result = parse(tokenize('var x = 3'))
    assert result == ast.VarExpr(
        name=ast.Identifier('x'),
        initializer=ast.Literal(3)
    )

    result_2 = parse(tokenize('{var x = 3}'))
    assert result_2 == ast.BlockExpr(
       statements=[
           ast.VarExpr(
            name=ast.Identifier('x'),
            initializer=ast.Literal(3)
           )
       ]
    )

    result_3 = parse(tokenize('{f(a); var x = 8; f(x)}'))
    assert result_3 == ast.BlockExpr(
        statements=[
            ast.FunctionExpr(
                function_name=ast.Identifier('f'),
                arguments=[
                    ast.Identifier('a')
                ]
            ),
            ast.VarExpr(
                name=ast.Identifier('x'),
                initializer=ast.Literal(8)
            ),
            ast.FunctionExpr(
                function_name=ast.Identifier('f'),
                arguments=[
                    ast.Identifier('x')
                ]
            )
        ]
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
    assert result == ast.BlockExpr(
        statements=[
            ast.BlockExpr(
                statements=[
                    ast.Identifier('a')
                ]
            ),
            ast.BlockExpr(
                statements=[
                    ast.Identifier('b')
                ]
            )
        ]
    )

    with pytest.raises(Exception, match= 'expected token "}" or ";"'):
        parse(tokenize('{ a b }'))

    result = parse(tokenize('{ if true then { a } b }'))
    assert result == ast.BlockExpr(
        statements=[
            ast.IfExpr(
                condition=ast.Identifier('true'),
                then_branch=ast.BlockExpr(
                    statements=[
                        ast.Identifier('a')
                    ]
                ),
                else_branch=None
            ),
            ast.Identifier('b')
        ]
    )

    result = parse(tokenize('{ if true then { a }; b }'))
    assert result == ast.BlockExpr(
        statements=[
            ast.IfExpr(
                condition=ast.Identifier('true'),
                then_branch=ast.BlockExpr(
                    statements=[
                        ast.Identifier('a')
                    ]
                ),
                else_branch=None
            ),
            ast.Identifier('b')
        ]
    )

    with pytest.raises(Exception, match= 'expected token "}" or ";"'):
        parse(tokenize('{ if true then { a } b c }'))

    result = parse(tokenize('{ if true then { a }; b; c }'))
    assert result == ast.BlockExpr(
        statements=[
            ast.IfExpr(
                condition=ast.Identifier('true'),
                then_branch=ast.BlockExpr(
                    statements=[
                        ast.Identifier('a')
                    ]
                ),
                else_branch=None
            ),
            ast.Identifier('b'),
            ast.Identifier('c')
        ]
    )

    result = parse(tokenize('{ if true then { a } else { b } c }'))
    assert result == ast.BlockExpr(
        statements=[
            ast.IfExpr(
                condition=ast.Identifier('true'),
                then_branch=ast.BlockExpr(
                    statements=[
                        ast.Identifier('a')
                    ]
                ),
                else_branch=ast.BlockExpr(
                    statements=[
                        ast.Identifier('b')
                    ]
                )
            ),
            ast.Identifier('c')
        ]
    )

    result = parse(tokenize('x = { { f(a) } { b } }'))
    assert result == ast.BinaryOp(
        left=ast.Identifier('x'),
        op='=',
        right=ast.BlockExpr(
            statements=[
                ast.BlockExpr(
                    statements=[
                        ast.FunctionExpr(
                            function_name=ast.Identifier('f'),
                            arguments=[
                                ast.Identifier('a')
                            ]
                        )
                    ]
                ),
                ast.BlockExpr(
                    statements=[
                        ast.Identifier('b')
                    ]
                )
            ]
        )
    )



# Task 8

# Task 9