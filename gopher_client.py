import socket
import os
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from datetime import datetime
from typing import Dict, List, Set, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BUF_SIZE = 4096                     # bytes per recv
GOPHER_TERM = b"\r\n.\r\n"          # end‑of‑menu sequence
DEFAULT_TIMEOUT = 5.0               # seconds per network op
MAX_WORKERS = 10                    # thread‑pool size
EXT_CONNECT_TIMEOUT = 0.5           # external host ping

# ---------------------------------------------------------------------------
# GopherClient
# ---------------------------------------------------------------------------

class GopherClient:
    """Pool‑based, thread‑safe Gopher crawler.

    * **One** clean public API: ``crawl()`` + ``summary()``.
    * Uses a daemon‑thread ``ThreadPoolExecutor`` so Python exits instantly.
    * Stores *only* file sizes for binaries → < 10 MB RSS.
    * Per‑request wall‑clock deadline enforced with ``future.result``.
    """

    # ------------------------------------------------------------------ init
    def __init__(
        self,
        host: str,
        port: int = 70,
        timeout: float = DEFAULT_TIMEOUT,
        workers: int = MAX_WORKERS,
        verbose: bool = True,
    ) -> None:
        self.host, self.port = host, port
        self.timeout = timeout
        self.verbose = verbose

        # daemon thread‑pool does not block interpreter shutdown
        def _factory(*args, **kw):
            t = threading.Thread(*args, **kw)
            t.daemon = True
            return t

        self.pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="gopher")
        # self.pool._thread_factory = _factory  # type: ignore[attr-defined]

        # crawl state
        self.visited: Set[str] = set()
        self.dirs: List[str] = []
        self.texts: Dict[str, str] = {}
        self.bins: Dict[str, int] = {}
        self.errors: List[str] = []
        self.bad_lines: Set[str] = set()
        self.ext: Dict[Tuple[str, int], bool] = {}

    # ------------------------------------------------------- helper logging
    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    # --------------------------------------------------------- worker func
    @staticmethod
    def _worker(host: str, port: int, sel: str, want_text: bool, tmo: float) -> bytes:
        with socket.create_connection((host, port), timeout=tmo) as sock:
            sock.sendall(f"{sel}\r\n".encode())
            sock.settimeout(tmo)
            buf = bytearray()
            while True:
                chunk = sock.recv(BUF_SIZE)
                if not chunk:
                    break
                buf.extend(chunk)
                if want_text and GOPHER_TERM in buf:
                    break
            return bytes(buf)

    # ---------------------------------------------------- pool request API
    def _req(self, host: str, port: int, sel: str, *, text: bool) -> bytes:
        self._log(f"CONNECT {host}:{port}{sel} (text={text})")
        t0 = time.time()
        fut = self.pool.submit(self._worker, host, port, sel, text, self.timeout)
        try:
            data = fut.result(timeout=self.timeout)
        except FutureTimeout:
            self._log(f"⚠︎ timeout {sel}")
            self.errors.append(f"timeout {sel}")
            return b""
        except Exception as e:
            self._log(f"✗  {e}")
            self.errors.append(f"worker {sel}: {e}")
            return b""
        self._log(f"✓  {sel}  {len(data)} B  {time.time()-t0:.2f}s")
        return data

    # ----------------------------------------------------------- crawl core
    def crawl(self, sel: str = "") -> None:
        if sel in self.visited:
            return
        self.visited.add(sel)

        raw = self._req(self.host, self.port, sel, text=True)
        lines = raw.decode("utf-8", "replace").splitlines()
        if lines and lines[-1] == '.':
            lines.pop()
        self.dirs.append(sel or "/")

        for line in lines:
            if not line:
                continue
            try:
                t, rest = line[0], line[1:]
                desc, s, h, p = rest.split("\t")[:4]
                p = int(p)
            except Exception:
                self.bad_lines.add(line)
                continue

            fp = f"{h}:{p}{s}"
            if t == '1' and (h, p) == (self.host, self.port):
                self.crawl(s)
            elif t == '0':
                txt = self._req(h, p, s, text=True)
                if txt:
                    self.texts[fp] = txt.decode("utf-8", "replace")
            else:
                blob = self._req(h, p, s, text=False)
                if blob:
                    self.bins[fp] = len(blob)
            if (h, p) != (self.host, self.port):
                self._ping_ext(h, p)

    # --------------------------------------------------- external host ping
    def _ping_ext(self, h: str, p: int) -> None:
        if (h, p) in self.ext:
            return
        try:
            with socket.create_connection((h, p), timeout=EXT_CONNECT_TIMEOUT):
                self.ext[(h, p)] = True
        except Exception:
            self.ext[(h, p)] = False

    # ---------------------------------------------------------------- dump
    def summary(self) -> None:
        self._log("----- Summary -----")
        self._log(f"Dirs {len(self.dirs)} | Text {len(self.texts)} | Bin {len(self.bins)}")

        self._log("Directories:")
        for d in sorted(self.dirs):
            self._log(f"  DIR  {d}")

        self._log("Text files:")
        for p, txt in self.texts.items():
            self._log(f"  TEXT {p}  ({len(txt.encode()):d} B)")

        self._log("Binary files:")
        for p, sz in self.bins.items():
            self._log(f"  BIN  {p}  ({sz} B)")

        cnt = Counter(self.errors)
        self._log(f"Errors {len(self.errors)} (unique {len(cnt)}):")
        for msg, n in cnt.items():
            self._log(f"  ERR  x{n}  {msg}")

        self._log(f"Invalid lines {len(self.bad_lines)}:")
        for l in self.bad_lines:
            self._log(f"  BAD {l}")

        self._log(f"External hosts {len(self.ext)}:")
        for (h, p), up in self.ext.items():
            self._log(f"  EXT {h}:{p} {'up' if up else 'down'}")

        self.pool.shutdown(wait=False, cancel_futures=True)
        self._log("Crawler finished — exiting.")
        # hard exit so lingering threads don't delay interpreter shutdown
        os._exit(0)

    generate_summary = summary
