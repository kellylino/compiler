from typing import Union
from dataclasses import  dataclass, field
from compiler.tokenizer import Location, SpecialLocation
from compiler.types import Type, Unit

@dataclass
class Expression:
    """Base class for AST nodes representing expressions."""
    loc: Union[Location, SpecialLocation]
    type: Type = field(kw_only=True, default_factory=lambda: Unit)

@dataclass
class Literal(Expression):
    value: int | bool

@dataclass
class Identifier(Expression):
    name: str

@dataclass
class UnaryOp(Expression):
    """AST node for a unary operation like `not x`"""
    op: str
    operand: Expression

@dataclass
class BinaryOp(Expression):
    """AST node for a binary operation like `A + B`"""
    left: Expression
    op: str
    right: Expression

@dataclass
class IfThenElse(Expression):
    """AST node for if-then-else expression"""
    condition: Expression
    then_branch: Expression
    else_branch: Expression | None = None

@dataclass
class WhileExpr(Expression):
    condition: Expression
    body: Expression

@dataclass
class FunctionExpr(Expression):
    function_name: Expression
    arguments: list[Expression]

@dataclass
class BlockExpr(Expression):
    statements: list[Expression]

@dataclass
class FunctionTypeExpr(Expression):
    param_types: list[Expression]
    return_type: Expression

@dataclass
class VarExpr(Expression):
    name: Expression
    initializer: Expression
    typed: Expression | None = None