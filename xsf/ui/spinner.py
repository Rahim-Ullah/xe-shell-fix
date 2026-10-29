"""
xsf.ui.spinner - Lightweight, non-intrusive animated terminal loader for AI and network operations.

Renders strictly on sys.stderr when connected to an interactive TTY so stdout (used for shell eval)
and automated test pipes are never polluted.
"""
import sys
import threading
import time
from typing import Optional


def flush_stdin() -> None:
    """
    Discards any stray keystrokes buffered in stdin while a blocking network spinner was running,
    preventing accidental Enter/y presses from bleeding into subsequent confirmation prompts.
    """
    try:
        if not sys.stdin.isatty():
            return
        if sys.platform == "win32":
            import msvcrt
            while msvcrt.kbhit():
                msvcrt.getwch()
        else:
            import termios
            termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
    except Exception:
        pass


class StatusSpinner:
    """
    Context-managed animated terminal spinner on stderr with live elapsed timer.
    """
    _FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")

    def __init__(self, message: str = "Consulting AI...", enabled: Optional[bool] = None):
        self.message = message
        self.enabled = sys.stderr.isatty() if enabled is None else bool(enabled)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._start_time = 0.0
        self._lock = threading.Lock()

    def update(self, message: str) -> None:
        with self._lock:
            self.message = message

    def _animate(self) -> None:
        idx = 0
        while not self._stop_event.is_set():
            elapsed = time.time() - self._start_time
            frame = self._FRAMES[idx % len(self._FRAMES)]
            with self._lock:
                msg = self.message
            try:
                line = f"\r  \033[1;36m{frame}\033[0m \033[90m{msg} ({elapsed:.1f}s)\033[0m\033[K"
                sys.stderr.write(line)
                sys.stderr.flush()
            except UnicodeEncodeError:
                ascii_frame = ("|", "/", "-", "\\")[idx % 4]
                line = f"\r  [{ascii_frame}] {msg} ({elapsed:.1f}s)\033[K"
                sys.stderr.write(line)
                sys.stderr.flush()
            except Exception:
                break
            idx += 1
            self._stop_event.wait(0.08)

    def __enter__(self) -> "StatusSpinner":
        if self.enabled:
            self._start_time = time.time()
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._animate, daemon=True)
            self._thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()

    def stop(self) -> None:
        if not self.enabled:
            return
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.3)
        try:
            sys.stderr.write("\r\033[K")
            sys.stderr.flush()
        except Exception:
            pass
        flush_stdin()
