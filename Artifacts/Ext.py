from dataclasses import dataclass

@dataclass(frozen=True)
class Ext:
  host    : str
  port    : int
  success : bool

