from compiler.tokenizer import Token
import compiler.ast as ast
from typing import Callable

left_associative_binary_operators = [
    ['or'],
    ['and'],
    ['==', '!='],
    ['<', '<=', '>', '>='],
    ['+', '-'],
    ['*', '/', '%'],
]

def parse(tokens: list[Token]) -> ast.Expression:
    if not tokens:
        raise Exception("Empty input: expected an expression")

    pos = 0

    # 'peek()' returns the token at 'pos',
    # or a special 'end' token if we're past the end of the token list.
    # This way we don't have to worry about going past the end elsewhere.
    def peek() -> Token:
        if pos < len(tokens):
            return tokens[pos]
        else:
            return Token(
                loc=tokens[-1].loc,
                type="end",
                text="",
            )

    # 'consume()' returns the token at 'pos' and increments 'pos' by one.
    #
    # If the optional parameter 'expected' is given,
    # it checks that the token being consumed has that text.
    # If 'expected' is a list, then the token must have one of the texts in the list.
    def consume(expected: str | list[str] | None = None) -> Token:
        # Python's "nonlocal" lets us modify `pos` without creating a local variable of the same name.
        nonlocal pos

        token = peek()
        if isinstance(expected, str) and token.text != expected:
            raise Exception(f'{token.loc}: expected "{expected}"')
        if isinstance(expected, list) and token.text not in expected:
            comma_separated = ", ".join([f'"{e}"' for e in expected])
            raise Exception(f'{token.loc}: expected one of: {comma_separated}')
        pos += 1
        return token

    def parse_int_literal() -> ast.Literal:
        if peek().type != 'int_literal':
            raise Exception(f'{peek().loc}: expected an integer literal')
        token = consume()
        return ast.Literal(token.loc, int(token.text))

    def parse_identifier() -> ast.Identifier:
        if peek().type != 'identifier':
            raise Exception(f'{peek().loc}: expected an identifier')
        token = consume()
        return ast.Identifier(token.loc, token.text)

    def parse_parenthesized() -> ast.Expression:
        consume('(')
        # Recursively call the top level parsing function to parse whatever is inside the parentheses.
        expr = parse_assignment()
        consume(')')
        return expr

    def parse_factor() -> ast.Expression:
        if peek().text == '(':
            return parse_parenthesized()
        elif peek().text == '{':
            return parse_block()
        elif peek().type == 'int_literal':
            return parse_int_literal()
        elif peek().type == 'identifier':
            identifier = parse_identifier()

            if peek().text == '(':
                return parse_function(identifier)
            else:
                return identifier
        else:
            raise Exception(f'{peek().loc}: expected "(", an integer literal or an identifier')

    def parse_if_expression() -> ast.Expression:
        token_if = consume('if')
        condition = parse_expression_no_var()

        consume('then')
        then_branch = parse_expression_no_var()

        else_branch = None
        if peek().text == 'else':
            consume('else')
            else_branch = parse_expression_no_var()

        return ast.IfThenElse(
            token_if.loc,
            condition,
            then_branch,
            else_branch
        )

    def parse_while_expression() -> ast.Expression:
        token_while = consume('while')
        condition = parse_expression_no_var()
        consume('do')
        body = parse_expression_no_var()

        return ast.WhileExpr(
            token_while.loc,
            condition,
            body
        )

    def parse_function(function_name: ast.Identifier) -> ast.Expression:
        token_func = consume('(')

        arguments = []
        if peek().text != ')':
            while True:
                arg = parse_expression_no_var()
                arguments.append(arg)

                if peek().text == ',':
                    consume(',')
                else:
                    break

        consume(')')
        return ast.FunctionExpr(token_func.loc, function_name, arguments)

    def parse_block() -> ast.Expression:
        token_block = consume('{')

        statements = []
        while peek().text != '}':
            arg = parse_assignment()
            if isinstance(arg, (ast.Identifier, ast.Literal)):
                if peek().text != '}' and peek().text != ';':
                    raise Exception(
                        'expected token "}" or ";"'
                    )
            statements.append(arg)

            if peek().text == ';':
                consume(';')

        consume('}')

        return ast.BlockExpr(token_block.loc, statements)

    def parse_var_expression() -> ast.Expression:
        token_var = consume('var')
        name = parse_factor()

        typed: ast.Expression | None = None

        if peek().text == ':':
            consume(':')
            if peek().text == '(':
                consume('(')
                param_types = []
                while True:
                    param_type = parse_factor()
                    param_types.append(param_type)

                    if peek().text == ',':
                        consume(',')
                    else:
                        break

                consume(')')
                consume('=')
                consume('>')
                return_type = parse_factor()

                typed = ast.FunctionTypeExpr(
                    token_var.loc,
                    param_types,
                    return_type
                )
            else:
                typed = parse_factor()

        consume('=')
        initializer = parse_assignment()

        return ast.VarExpr(
            token_var.loc,
            name,
            initializer,
            typed
        )

    def parse_unary_expression() -> ast.Expression:
        token_op = consume()
        op = token_op.text
        if peek().text == 'not' or peek().text == '-':
            operand = parse_unary_expression()
        else:
            operand = parse_factor()
        return ast.UnaryOp(token_op.loc, op, operand)

    def parse_expression_no_var() -> ast.Expression:
        if peek().text == 'var':
            raise Exception(
                "unexpected token var, var is only allowed directly inside blocks {} and in top-level expressions"
            )
        return parse_assignment()

    def make_binary_parser(operators_levels: list[list[str]], level: int) -> Callable:

        if level >= len(operators_levels):
            def parse_base() -> ast.Expression:
                if peek().text == 'if':
                    return parse_if_expression()
                elif peek().text == 'while':
                    return parse_while_expression()
                elif peek().text == 'var':
                    return parse_var_expression()
                elif peek().text == 'not' or peek().text == '-':
                    return parse_unary_expression()
                return parse_factor()
            return parse_base

        # Recursive call for next-higher-precedence level
        next_level_parser = make_binary_parser(operators_levels, level + 1)
        current_ops = set(operators_levels[level])

        def parse_level() -> ast.Expression:
            left = next_level_parser()
            while peek().text in current_ops:
                token_op = consume()
                op = token_op.text
                right = next_level_parser()
                left = ast.BinaryOp(token_op.loc, left, op, right)
            return left

        return parse_level

    parse_expression = make_binary_parser(left_associative_binary_operators, 0)

    def parse_assignment() -> ast.Expression:
        left = parse_expression()
        if peek().text == '=':
            token = consume('=')
            right = parse_assignment()  # '=' right-associative
            return ast.BinaryOp(token.loc, left, '=', right)
        return left

    # result = parse_assignment()

    # if peek().type != 'end':
    #     raise Exception(f'{peek().loc}: unexpected token "{peek().text}" after complete expression')

    # return result

    statements = []

    while peek().type != 'end':
        stmt = parse_assignment()
        statements.append(stmt)

        if peek().text == ';':
            consume(';')
        elif peek().type != 'end':
            raise Exception(
                f'{peek().loc}: unexpected token "{peek().text}" after complete expression'
            )

    if len(statements) == 1:
        return statements[0]

    return ast.BlockExpr(
        statements[0].loc,
        statements
    )


