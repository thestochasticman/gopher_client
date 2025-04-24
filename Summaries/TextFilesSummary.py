from typing_extensions import Self
from dataclasses import dataclass
from dataclasses import field
from Artifacts.TextFile import TextFile
from colorama import init, Fore, Back, Style
from collections import OrderedDict
from dataclasses import asdict
from pandas import DataFrame
from pandas import set_option

@dataclass(frozen=True)
class TextFilesSummary:
  files         : dict[str, TextFile]
  files_by_size : OrderedDict = field(init=False)
  df            : DataFrame   = field(init=False)

  def __post_init__(s: Self):
    sorted_items = sorted(
      s.files.items(),
      key=lambda kv: kv[1].size,            # kv = (path, TextFile)
      reverse=True
    )
    object.__setattr__(s, "files_by_size", OrderedDict(sorted_items))

  def generate_summary(s: Self):
    init(autoreset=True)
    print(Style.BRIGHT + Fore.GREEN + f"The full paths of the {len(s.files)} files and the size of the data received from them is as follows")
    # for i, (sel, file) in enumerate(s.files.items()):
    records = []
    file: TextFile
    for i, (sel, file) in enumerate(s.files_by_size.items()):
      if file.success:
        colour = Fore.GREEN
      else:
        colour = Fore.RED
      print(colour + str(i+1).zfill(2) + ': ' + file.path + ': ' + str(file.size) + ': ' )
      records += [asdict(file)]
   
    df = DataFrame.from_records(records, index=list(range(1, len(s.files) + 1)))
    df = df.rename(columns={'size': 'size(bytes)'})
    df['path'] = df['path'].apply(lambda x: x[:50])
    print(Fore.GREEN + df[['path', 'size(bytes)', 'error', 'success']].to_string(max_colwidth=100))
    


    # print(Fore.GREEN + df.to_string(max_colwidth=100))
    # print(Fore.GREEN + df[['path', 'content', 'size(bytes)']].to_string(max_colwidth=100))


    
    
