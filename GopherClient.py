import socket
import time
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from datetime import datetime
from typing import Set, Tuple
from typing_extensions import Self
from Summaries.DirsSummary import DirsSummary
from Summaries.TextFilesSummary import TextFilesSummary
from Summaries.BinaryFilesSummary import BinaryFilesSummary
from Summaries.ExtSummary import ExtsSummary
from Artifacts.Dir import Dir
from Artifacts.TextFile import TextFile
from Artifacts.BinaryFile import BinaryFile
from Artifacts.Ext import Ext
from colorama import init, Fore, Back, Style

BUF_SIZE = 4096                     # bytes per recv
GOPHER_TERM = b".\r\n"              # end‑of‑menu sequence
DEFAULT_TIMEOUT = 5                 # seconds per network op
MAX_WORKERS = 10                    # thread‑pool size
EXT_CONNECT_TIMEOUT = 2.0           # external host ping
MAX_DOWNLOAD_SIZE = 1024 * 1024     # 1 MB max file size

class GopherClient:
  def __init__(
    s: Self,
    host: str,
    port: int = 70,
    timeout: float = DEFAULT_TIMEOUT,
    workers: int = MAX_WORKERS,
    verbose: bool = True,
  ):
    def _factory(*args, **kwargs):
      t = threading.Thread(*args, **kwargs)
      t.daemon = True
      return t
    s.host, s.port = host, port
    s.timeout = timeout
    s.verbose = verbose
    s.pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="client")
    s.pool._thread_factory = _factory
    s.visited       : Set[str] = set()
    s.bad_lines     : Set[str] = set()
    s.dirs          : dict[str, Dir] = dict()
    s.text_files    : dict[str, TextFile] = dict()
    s.binary_files  : dict[str, BinaryFile] = dict()
    s.exts          : dict[Tuple[str, int], Ext] = {}

  def _log(s: Self, msg: str) -> None:
    if s.verbose: print(f"[{datetime.now().strftime("%H:%M:%S")}] {msg}") 
  
  @staticmethod
  def _worker(
    host: str,
    port: int,
    sel: str,
    want_text: bool,
    timeout: float
  )->Tuple[bytes, bool, bool, bool]:
    
    buf = bytearray()
    total_read = 0
    start_time = time.time()
    error = ""
    path = f"{host}:{port}{sel}"
    try:
      with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(f"{sel}\r\n".encode())
        sock.settimeout(timeout)
        path = f"{host}:{port}{sel}"
        while True:
          if (time.time() - start_time) > timeout:
            error = f"INTERRUPTED, Max Time Limit of {timeout} seconds reached for connection: {path}"
            break
          elif total_read >= (MAX_DOWNLOAD_SIZE - BUF_SIZE):
            error = f"INTERRUPTED, Download Limit of {MAX_DOWNLOAD_SIZE} KB exceeded: {path}"
            break
          elif want_text and buf.endswith(GOPHER_TERM):
            break
          try:
            chunk = sock.recv(BUF_SIZE)
            if chunk:
              buf.extend(chunk)
              total_read += len(chunk)
            if not chunk:
              return bytes(buf), error
          except socket.timeout:
            error = f"INTERRUPTED, Timed out while waiting to receive data from socket: {path}"
            if sel == 'firehose':
              print('this is firehose', buf)
          except Exception as e:
            error = f"INTERRUPTED, Some other Exception: {sel}"
            break
    except socket.timeout:
      error = f"FAILED, Timed out while connecting in {timeout} seconds: {path}"
    return bytes(buf), error

  def _req(s: Self, host: str, port: int, sel: str, text: bool) -> bytes:
    path = f"{host}:{port}{sel}"
    s._log(f"CONNECT {path}")
    
    t0 = time.time()
    fut = s.pool.submit(s._worker, host, port, sel, text, s.timeout)
    error = ''
    try:
        data, error = fut.result(timeout=s.timeout * 2)
        s._log(error if error else f"Request Completed  {path}  {len(data)}  {time.time()-t0:.2f}s")
        return path, data, error
    except FutureTimeout:
        if fut.done():
          data, error = fut.result()
          error = error or f"INTERRUPTED, Finished after worker thread timeout ({s.timeout * 2}s): {path}"
        else:
          path, error = b"", f"INTERRUPTED, FutureTimeout after {s.timeout}s :{path}"
        s._log(error)
        return path, b"", error
    except Exception as e:
        s._log(f"FAILED, Received {e} for {path}")
        error = f"worker {path}: {e}"
        return path, b"", error

  def _ping_ext(s: Self, h: str, p: int) -> None:
    if (h, p) in s.exts: return
    try:
      with socket.create_connection((h, p), timeout=EXT_CONNECT_TIMEOUT):
        s.exts[(h, p)] = Ext(h, p, True)
    except Exception:
      s.exts[(h, p)] = Ext(h, p, False)

  def explore_line(s: Self, line: str)->tuple[str, str, str, str, int]:
    _type, rest = line[0], line[1:]
    desc, sel, host, port = rest.split("\t")[:4]
    port= int(port)
    path = f"{host}:{port}{sel}"

    if (host, port) != (s.host, s.port):
      s._ping_ext(host, port)
      return  
    if    _type == "1" and (host, port) == (s.host, s.port): s.index(sel)
    elif  _type == "0": s.text_files[path] = TextFile(*s._req(host, port, sel, True))
    else              : s.binary_files[path] = BinaryFile(*s._req(host, port, sel, False))

    # if (host, port) != (s.host, s.port):
    #   s._ping_ext(host, port)

  def index(s: Self, sel: str = ""):
    if sel in s.visited: return
    s.visited.add(sel)
    s.dirs[sel or "/"] = Dir(*s._req(s.host, s.port, sel, text=True))
    for line in s.dirs[sel or "/"].lines:
      if not line: continue
      try: s.explore_line(line)
      except Exception: s.bad_lines.add(line)

    if sel == "":
      s._log("index DONE, TERMINATING")
      s.pool.shutdown(wait=True)
      return
    
  def generate_summary(s: Self):
    dirs_summary = DirsSummary(s.dirs)
    dirs_summary.generate_summary()
    print('-' * 150)
    text_files_summary = TextFilesSummary(s.text_files)
    text_files_summary.generate_summary()
    print('-' * 150)
    binary_files_summary = BinaryFilesSummary(s.binary_files)
    binary_files_summary.generate_summary()
    print('-' * 150)
    ext_summary = ExtsSummary(s.exts)
    ext_summary.generate_summary()
    print('-' * 150)

    print(Style.BRIGHT + Fore.GREEN + f"Other bad search")
    print(client.bad_lines)
    
  
if __name__ == "__main__":
  client = GopherClient("comp3310.ddns.net", 70)
  start = time.time()
  client.index()
  client.generate_summary()

  # file: TextFile
  # for file in client.text_files:
  #   print(file, client.text_files[file].error)

  # file: BinaryFile
  # for file in client.binary_files:
  #   print(file, client.binary_files[file].error)
    