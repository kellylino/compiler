from dataclasses import dataclass

@dataclass
class Expression:
    """Base class for AST nodes representing expressions."""

@dataclass
class Literal(Expression):
    value: int | bool

@dataclass
class Identifier(Expression):
    name: str

@dataclass
class BinaryOp(Expression):
    """AST node for a binary operation like `A + B`"""
    left: Expression
    op: str
    right: Expression

@dataclass
class IfExpr(Expression):
    """AST node for if-then-else expression"""
    condition: Expression
    then_branch: Expression
    else_branch: Expression | None  #optional

@dataclass
class WhileExpr(Expression):
    condition: Expression
    body: Expression

@dataclass
class FunctionExpr(Expression):
    """AST node for function calls like f(x, y + z)"""
    function_name: Expression
    arguments: list[Expression]

@dataclass
class UnaryOp(Expression):
    """AST node for a unary operation like `not x`"""
    op: str
    operand: Expression

@dataclass
class BlockExpr(Expression):
    statements: list[Expression]

@dataclass
class VarExpr(Expression):
    name: str
    initializer: Expression