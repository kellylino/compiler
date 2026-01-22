from compiler.tokenizer import Token
import compiler.ast as ast

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
        nonlocal pos # Python's "nonlocal" lets us modify `pos`
                     # without creating a local variable of the same name.
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
        return ast.Literal(int(token.text))

    def parse_identifier() -> ast.Identifier:
        if peek().type != 'identifier':
            raise Exception(f'{peek().loc}: expected an identifier')
        token = consume()
        return ast.Identifier(token.text)

    def parse_parenthesized() -> ast.Expression:
        consume('(')
        # Recursively call the top level parsing function to parse whatever is inside the parentheses.
        expr = parse_expression()
        consume(')')
        return expr

    def parse_factor() -> ast.Expression:
        if peek().text == '(':
            return parse_parenthesized()
        elif peek().type == 'int_literal':
            return parse_int_literal()
        elif peek().type == 'identifier':
            return parse_identifier()
        else:
            raise Exception(f'{peek().loc}: expected "(", an integer literal or an identifier')

    def parse_term() -> ast.Expression:
        left = parse_factor()

        while peek().text in ['*', '/']:
            operator_token = consume()
            operator = operator_token.text
            right = parse_factor()
            left = ast.BinaryOp(
                left,
                operator,
                right
            )
        return left

    def left_parse_expression() -> ast.Expression:
        # Parse the first term. (1 - 2) + 3
        left = parse_term()

        # While there are more `+` or '-'...
        while peek().text in ['+', '-']:
            # Move past the '+' or '-'.
            operator_token = consume()
            operator = operator_token.text

            # Parse the operator on the right.
            right = parse_term()

            # Combine it with the stuff we've accumulated on the left so far.
            left = ast.BinaryOp(
                left,
                operator,
                right
            )

        return left

    def right_parse_expression() -> ast.Expression:
        # Parse the first term. 1 - (2 + 3)
        left = parse_term()

        # While there are more `+` or '-'...
        if peek().text in ['+', '-']:
            # Move past the '+' or '-'.
            operator_token = consume()
            operator = operator_token.text

            # Parse the operator on the right.
            right = right_parse_expression()

            # Combine it with the stuff we've accumulated on the right so far.
            return ast.BinaryOp(left, operator, right)

        return left

    def parse_expression() -> ast.Expression:

        left = parse_term()

        while peek().text in ['+', '-']:
            operator_token = consume()
            operator = operator_token.text
            right = parse_term()
            left = ast.BinaryOp(
                left,
                operator,
                right
            )

        return left

    result = parse_expression()

    if peek().type != 'end':
        raise Exception(f'{peek().loc}: unexpected token "{peek().text}" after complete expression')

    return result