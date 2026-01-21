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