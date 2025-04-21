import socket
import threading
import time
from datetime import datetime
from typing import List, Set, Dict, Tuple

TERMINATOR = b"\r\n.\r\n"  # canonical Gopher end‑marker

class TimeoutError(Exception):
    """Raised when a worker thread exceeds its wall‑clock budget."""

# ---------------------------------------------------------------------------
# Utility: run a function in a thread and kill its socket if it overstays
# ---------------------------------------------------------------------------

def run_with_timeout(fn, args, timeout: float):
    """Run *fn(*args) in a background Thread.  If it does not finish within
    *timeout* seconds, attempt to close any socket passed as the first arg
    (convention in this file) and raise TimeoutError in the main thread."""
    result_holder: Dict[str, object] = {}
    err_holder: List[Exception] = []

    def wrapper():
        try:
            result_holder["value"] = fn(*args)
        except Exception as e:
            err_holder.append(e)

    t = threading.Thread(target=wrapper, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        # First arg is expected to be a socket – try to terminate politely.
        sock = args[0]
        if isinstance(sock, socket.socket):
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                sock.close()
            except Exception:
                pass
        raise TimeoutError("worker exceeded %s s" % timeout)
    if err_holder:
        raise err_holder[0]
    return result_holder.get("value")

# ---------------------------------------------------------------------------
# Gopher client
# ---------------------------------------------------------------------------
class GopherClient:
    """Thread‑aware Gopher crawler: every network request runs in its own
    worker thread; the main thread enforces a wall‑clock deadline and kills
    the socket if the worker takes too long."""

    def __init__(self, host: str, port: int = 70, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout  # seconds allowed per request
        self.visited: Set[str] = set()
        self.directories: List[str] = []
        self.text_files: Dict[str, str] = {}
        self.binary_files: Dict[str, bytes] = {}
        self.errors: List[str] = []
        self.invalid_refs: Set[str] = set()
        self.external_servers: Dict[Tuple[str, int], bool] = {}

    # ---------------- internal logging ----------------
    def _log(self, msg: str):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    # ---------------- low‑level worker ----------------
    @staticmethod
    def _do_request(sock: socket.socket, selector: str, want_text: bool):
        """Worker body: send selector, read till terminator (text) or until
        server closes (binary). Returns bytes."""
        sock.sendall(f"{selector}\r\n".encode())
        buf = bytearray()
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf.extend(chunk)
            if want_text and TERMINATOR in buf:
                break
        return bytes(buf)

        # ---------------- public request helper (clean single flow) ----------------
    def request(self, host: str, port: int, selector: str, want_text: bool = True) -> bytes:
        """Send one Gopher request in a worker thread; main thread enforces
        *self.timeout*.  Emits exactly one log line for success, timeout, or
        error.  No duplicated code paths."""

        self._log(f"CONNECT {host}:{port}{selector} (text={want_text})")
        start = time.time()

        # 1️⃣ connect
        try:
            sock = socket.create_connection((host, port), timeout=self.timeout)
        except Exception as e:
            self._log(f"✗  connect error → {e}")
            self.errors.append(f"connect {selector}: {e}")
            return b""

        # 2️⃣ run worker with timeout guard
        try:
            data: bytes = run_with_timeout(self._do_request, (sock, selector, want_text), self.timeout)
        except TimeoutError:
            self._log(f"⚠︎ timeout after {self.timeout}s → {selector}")
            self.errors.append(f"timeout {selector}")
            return b""
        except Exception as e:
            self._log(f"✗  recv error → {e}")
            self.errors.append(f"recv {selector}: {e}")
            return b""
        finally:
            try:
                sock.close()
            except Exception:
                pass

        # 3️⃣ success
        self._log(f"✓  finished {selector} in {time.time() - start:.2f}s, bytes={len(data)}")
        return data

    # ---------------- crawler logic ---------------- ----------------
    def crawl(self, selector: str = ""):
        if selector in self.visited:
            return
        self.visited.add(selector)
        raw = self.request(self.host, self.port, selector, want_text=True)
        lines = raw.decode("utf-8", "replace").splitlines()
        if lines and lines[-1] == '.':
            lines.pop()  # remove terminator
        self.directories.append(selector)
        for line in lines:
            if not line:
                continue
            try:
                t = line[0]
                desc, sel, host, port = line[1:].split("\t")[:4]
                port = int(port)
            except Exception:
                self.invalid_refs.add(line)
                continue

            fp = f"{host}:{port}{sel}"
            if t == '1' and host == self.host and port == self.port:
                self.crawl(sel)
            elif t == '0':
                txt_b = self.request(host, port, sel, want_text=True)
                if txt_b:
                    text = txt_b.decode("utf-8", "replace")
                    self.text_files[fp] = text
            else:  # binary or unknown
                bin_b = self.request(host, port, sel, want_text=False)
                if bin_b:
                    self.binary_files[fp] = bin_b
            if (host, port) != (self.host, self.port):
                self.ping_external(host, port)

    # ---------------- external ping ----------------
    def ping_external(self, host: str, port: int):
        if (host, port) in self.external_servers:
            return
        try:
            run_with_timeout(socket.create_connection, ((host, port),), 2)
            self.external_servers[(host, port)] = True
        except Exception:
            self.external_servers[(host, port)] = False

        # ---------------- summary ----------------
        # ---------------- summary ----------------
    def summary(self):
        self._log("----- Detailed Summary -----")

        # Directories
        self._log(f"Directories ({len(self.directories)}):")
        for d in sorted(self.directories):
            self._log(f"  DIR  {d or '/'}")

        # Text files (list only)
        self._log(f"Text files ({len(self.text_files)}):")
        for path, content in self.text_files.items():
            self._log(f"  TEXT {path}  (bytes={len(content.encode('utf-8'))})")

        # Binary files with size
        self._log(f"Binary files ({len(self.binary_files)}):")
        for path, blob in self.binary_files.items():
            self._log(f"  BIN  {path}  (bytes={len(blob)})")

        # Errors (source list)
        self._log(f"Errors ({len(self.errors)}):")
        for e in self.errors:
            self._log(f"  ERR  {e}")

        # Invalid lines
        self._log(f"Invalid Gopher lines ({len(self.invalid_refs)}):")
        for l in self.invalid_refs:
            self._log(f"  BAD  {l}")

        # External servers status
        self._log(f"External servers ({len(self.external_servers)}):")
        for (h, p), up in self.external_servers.items():
            status = "up" if up else "down"
            self._log(f"  EXT  {h}:{p} is {status}")

    generate_summary = summary

if __name__ == "__main__":
    client = GopherClient("comp3310.ddns.net", 70)
    client.crawl()
    client.summary()
