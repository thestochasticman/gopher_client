from dataclasses import dataclass
from typing_extensions import Self
from dataclasses import field
from json import dump
from os.path import exists
from os import makedirs
from os.path import join

@dataclass(frozen=True)
class TextFile:
  path            : str     
  raw             : bytes
  error           : str
  log_dir         : str
  content         : str = field(init=False)
  size            : int = field(init=False)
  success         : bool = field(init=False)
  text_files_dir  : str = field(init=False)

  def __post_init__(s: Self):
    
    object.__setattr__(s, 'content', s.raw.decode("utf-8", "replace"))
    object.__setattr__(s, 'success', True if not s.error else False)
    object.__setattr__(s, 'size', len(s.raw))
    object.__setattr__(s, 'text_files_dir', join(f"{s.log_dir}", "TextFiles"))

    if not exists(s.text_files_dir): makedirs(s.text_files_dir, exist_ok=True)
    destination = join(f"{s.text_files_dir}", f"{s.path.replace('/', '-')}.json")
    dump(s.content, open(destination, 'w+'))



  def __str__(s: Self)->str: return s.path
