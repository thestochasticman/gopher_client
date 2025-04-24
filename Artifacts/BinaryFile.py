from typing_extensions import Self
from dataclasses import dataclass
from dataclasses import field
from types import NoneType

@dataclass(frozen=True)
class BinaryFile:
  path    : str
  raw     : bytes
  error   : str
  size    : int = field(init=False)
  success : bool = field(init=False)

  def __post_init__(s: Self):
    if not s.error:
      object.__setattr__(s, 'size', len(s.raw))
      object.__setattr__(s, 'success', True)
    else:
  
      object.__setattr__(s, 'size', len(s.raw))
      object.__setattr__(s, 'success', False)
