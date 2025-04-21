import socket
import os
import time
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from datetime import datetime
from typing import Dict, List, Set, Tuple
from typing_extensions import Self
from Dir import Dir
from TextFile import TextFile
from BinaryFile import BinaryFile
from Ext import Ext
from socket import timeout as socket_timeout
from Data import Data

BUF_SIZE = 4096                     # bytes per recv
GOPHER_TERM = b"\r\n.\r\n"          # end‑of‑menu sequence
DEFAULT_TIMEOUT = 5.0               # seconds per network op
MAX_WORKERS = 10                    # thread‑pool size
EXT_CONNECT_TIMEOUT = 0.5           # external host ping


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
    s.pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix='client')
    s.pool._thread_factory = _factory
    s.visited       : Set[str] = set()
    s.bad_lines     : Set[str] = set()
    s.dirs          : dict[str, Dir] = dict()
    s.text_files    : dict[str, TextFile] = dict()
    s.binary_files  : dict[str, BinaryFile] = dict()
    s.exts          : dict[Tuple[str, int], Ext] = {}

  def _log(s: Self, msg: str) -> None:
    if s.verbose: print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

  @staticmethod
  def _worker(
    host: str,
    port: int,
    sel: str,
    want_text: bool,
    timeout: float
  )->bytes:
    with socket.create_connection((host, port), timeout=timeout) as sock:
      sock.sendall(f"{sel}\r\n".encode())
      sock.settimeout(timeout)
      buf = bytearray()

      socket_timeout_occured = False
      max_download_occured = False
      total_timeout_occured = False

      while True:
        try:
          chunk = sock.recv(BUF_SIZE)
        except socket_timeout:
          socket_timeout_occured = True

        if not chunk: break
        buf.extend(chunk)
        if want_text and GOPHER_TERM in buf: break
    return bytes(buf), socket_timeout_occured, max_download_occured,total_timeout_occured
  
  def _req(self, host: str, port: int, sel: str, text: bool) -> bytes:
    self._log(f"CONNECT {host}:{port}{sel} (text={text})")
    t0 = time.time()
    fut = self.pool.submit(self._worker, host, port, sel, text, self.timeout)
    error = ''
    try:
        result = fut.result(timeout=self.timeout)
        data = 
        self._log(f"CONNECTED  {sel}  {len(data)} B  {time.time()-t0:.2f}s")
        return sel, data, error
    except FutureTimeout:
        self._log(f"TIMEOUT {sel}")
        # self.errors.append(f"timeout {sel}")
        error = "TIMEOUT {sel}"
        return sel, b"", error
    except Exception as e:
        self._log(f"FAILED {sel} {e}")
        error += f"worker {sel}: {e}"
        return sel, b"", error
    
  def _ping_ext(s: Self, h: str, p: int) -> None:
    if (h, p) in s.exts: return
    try:
      with socket.create_connection((h, p), timeout=EXT_CONNECT_TIMEOUT):
        s.exts[(h, p)] = Ext(h, p, True)
    except Exception:
      s.exts[(h, p)] = Ext(h, p, False)
  
  # @staticmethod
  def explore_line(s: Self, line: str)->tuple[str, str, str, str, int]:
    _type, rest = line[0], line[1:]
    desc, sel, host, port = rest.split("\t")[:4]
    port= int(port)
    path = f"{host}:{port}{sel}"
    if    _type == '1' and (host, port) == (s.host, s.port): s.crawl(sel)
    elif  _type == '0': s.text_files[path] = TextFile(*s._req(host, port, sel, True))
    else              : s.binary_files[path] = BinaryFile(*s._req(host, port, sel, False))
    
    if (host, port) != (s.host, s.port):
      s._ping_ext(host, port)

  def crawl(s: Self, sel: str = ''):
    if sel in s.visited: return
    s.visited.add(sel)
    s.dirs[sel or '/'] = Dir(*s._req(s.host, s.port, sel, text=True))
    for line in s.dirs[sel or '/'].lines:
      if not line: continue
      try: s.explore_line(line)
      except Exception: s.bad_lines.add(line)
    
    if sel == '':
      # s.pool.shutdown(wait=True, cancel_futures=True)
      s._log('CRAWL DONE, TERMINATING')
      return

if __name__ == '__main__':
  client = GopherClient("comp3310.ddns.net", 70)
  client.crawl()
  client.pool.shutdown(wait=True)
  print(len(client.binary_files))
  print(len(client.dirs))
  print(len(client.text_files))
  print(len(client.exts))
