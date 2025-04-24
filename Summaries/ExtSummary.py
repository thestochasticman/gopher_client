from typing_extensions import Self
from dataclasses import dataclass
from dataclasses import field
from Artifacts.Ext import Ext
from colorama import init, Fore, Back, Style
from collections import OrderedDict
from dataclasses import asdict
from pandas import DataFrame
from pandas import set_option

@dataclass(frozen=True)
class ExtsSummary:
  exts : dict[str, Ext]
  df   : DataFrame   = field(init=False)

  def generate_summary(s: Self):
    records = []
    for path in s.exts:
      records += [asdict(s.exts[path])]
    
    df = DataFrame.from_records(records, index=range(1, len(records) + 1))
    print(Fore.GREEN + df.to_string())


    # print(Fore.GREEN + df.to_string(max_colwidth=100))
    # print(Fore.GREEN + df[['path', 'content', 'size(bytes)']].to_string(max_colwidth=100))


    
    
