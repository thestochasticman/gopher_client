from typing_extensions import Self
from dataclasses import dataclass
from dataclasses import field
from json import dump
from os.path import exists
from os import makedirs
from os.path import join

@dataclass(frozen=True)
class BinaryFile:
  path              : str
  raw               : bytes
  error             : str
  log_dir           : str
  size              : int = field(init=False)
  success           : bool = field(init=False)
  content           : bool = field(init=False)
  binary_files_dir  : str = field(init=False)

  def __post_init__(s: Self):
    object.__setattr__(s, 'size', len(s.raw))
    object.__setattr__(s, 'success', False if s.error else True)
    object.__setattr__(s, 'content', s.raw.decode("utf-8", "replace"))
    object.__setattr__(s, 'binary_files_dir', join(f"{s.log_dir}", "BinaryFiles"))

    if not exists(s.binary_files_dir): makedirs(s.binary_files_dir, exist_ok=True)
    destination = join(f"{s.binary_files_dir}", f"{s.path.replace('/', '-')}.json")
    dump(s.content, open(destination, 'w+'))