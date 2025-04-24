from dataclasses import dataclass
from typing_extensions import Self
from dataclasses import field

@dataclass(frozen=True)
class TextFile:
  sel       : str     
  raw       : bytes
  error     : str
  content   : str = field(init=False)
  size      : int = field(init=False)
  success   : str = field(init=False)

  def __post_init__(s: Self):
    if not s.error:
      object.__setattr__(s, 'content', s.raw.decode("utf-8", "replace"))
      object.__setattr__(s, 'success', True)
    
    else:
      object.__setattr__(s, 'content', '')
      object.__setattr__(s, 'success', False)

    object.__setattr__(s, 'size', len(s.raw))

  def __str__(s: Self)->str: return s.path
