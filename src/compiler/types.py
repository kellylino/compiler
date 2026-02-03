from dataclasses import  dataclass
from typing import Tuple

@dataclass
class Type:
    pass

@dataclass
class IntType(Type):
    pass

@dataclass
class BoolType(Type):
    pass

@dataclass
class UnitType(Type):
    pass

@dataclass
class FunType(Type):
    params: Tuple[Type, ...]
    return_type: Type

Int = IntType()
Bool = BoolType()
Unit = UnitType()