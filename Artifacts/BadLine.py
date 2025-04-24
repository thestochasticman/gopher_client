from dataclasses import dataclass

@dataclass(frozen=True)
class BadLine:
  line  : str
  dir   : str
  error : str