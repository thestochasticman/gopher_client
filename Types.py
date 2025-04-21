from dataclasses import dataclass

@dataclass(frozen=True)
class Types:
  Dir : str = 'dir'
  Text: str = 'text'
  Bin : str = 'bin'