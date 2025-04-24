from dataclasses import dataclass
from typing_extensions import Self
from dataclasses import field

@dataclass(frozen=True)
class TextFile:
  path      : str     
  raw       : bytes
  error     : str
  content   : str = field(init=False)
  size      : int = field(init=False)
  success   : bool = field(init=False)

  def __post_init__(s: Self):
    object.__setattr__(s, 'content', s.raw.decode("utf-8", "replace"))
    object.__setattr__(s, 'success', True if not s.error else False)
    object.__setattr__(s, 'size', len(s.raw))

  def __str__(s: Self)->str: return s.path
