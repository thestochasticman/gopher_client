from typing_extensions import Self
from dataclasses import dataclass
from dataclasses import field
from Artifacts.BadLine import BadLine
from colorama import init, Fore, Back, Style
from collections import OrderedDict
from dataclasses import asdict
from pandas import DataFrame
from pandas import set_option

@dataclass(frozen=True)
class BadLinesSummary:
  bad_lines : dict[str, BadLine]
  df   : DataFrame   = field(init=False)

  def generate_summary(s: Self):
    records = []
    for line in s.bad_lines:
      records += [asdict(s.bad_lines[line])]
    
    print(Style.BRIGHT + Fore.RED + f"Other errors encountered when exploring dirs and files are as follows:")
    df = DataFrame.from_records(records, index=range(1, len(records) + 1))
    print(Fore.RED + df[['error']].to_string())

    # print(Fore.GREEN + df.to_string(max_colwidth=100))
    # print(Fore.GREEN + df[['path', 'content', 'size(bytes)']].to_string(max_colwidth=100))


    
    
