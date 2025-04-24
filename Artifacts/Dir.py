from dataclasses import dataclass
from typing_extensions import Self
from dataclasses import field

@dataclass(frozen=True)
class Dir:
  path    : str     
  raw     : bytes
  error   : str       = ''
  lines   : list[str] = field(init=False)
  success : bool      = field(init=False)


  def __post_init__(s: Self):
    lines = s.raw.decode("utf-8", "replace").splitlines()
    if lines and lines[-1] == '.': lines.pop()
    object.__setattr__(s, 'lines', s.raw.decode("utf-8", "replace").splitlines())
    object.__setattr__(s, 'success', False if s.error else True)


  def __str__(s: Self)->str: return s.path
