from typing_extensions import Self
from dataclasses import dataclass
from dataclasses import field
from Artifacts.TextFile import TextFile
from colorama import init, Fore, Back, Style

@dataclass(frozen=True)
class TextFilesSummary:
  files: dict[str, TextFile]

  file_size: dict[str, TextFile] = field(init=False)

  def __post_init__(s: Self):
    file_size = {file: s.files[file].size for file in s.files}
    object.__setattr__(s, 'file_size', file_size)

  def generate_summary(s: Self):
    init(autoreset=True)
    print(Style.BRIGHT + Fore.RED + f"The full paths of the {len(s.files)} directories are as follows")
    # for i, (sel, file) in enumerate(s.files.items()):
    file: TextFile
    for sel, file in s.files.items():
      print(Fore.RED + file.path + ': ' + str(file.size))
      # if sel.__contains__('firehose')
