from typing_extensions import Self
from dataclasses import dataclass
from Dir import Dir
from colorama import init, Fore, Back, Style

@dataclass(frozen=True)
class DirsSummary:
  dirs: dict[str, Dir]

  def generate_summary(s: Self):
    init(autoreset=True)
    print(Style.BRIGHT + Fore.RED + f"The full paths of the {len(s.dirs)} directories are as follows")
    for i, (sel, dir) in enumerate(s.dirs.items()):
      print(Fore.RED + str(i+1) + ': ' + (dir.sel or '/(Root)'))
