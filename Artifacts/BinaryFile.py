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
  content : bool = field(init=False)

  def __post_init__(s: Self):
    object.__setattr__(s, 'size', len(s.raw))
    object.__setattr__(s, 'success', False if s.error else True)
    object.__setattr__(s, 'content', s.raw.decode("utf-8", "replace"))

