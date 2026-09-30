"""
SnapGuard - on-device screen privacy filter (prototype)

Pipeline: screen capture -> OCR -> regex detection -> pixelate -> preview window.
The preview window is the *outgoing* (shared) feed. Your real screen is untouched.

Run:            python snapguard.py
Run for demo:   python snapguard.py --record   (preview stays visible to screen recorders)

Controls
  Ctrl+Alt+B : opt-out of blur for the CURRENT window (auto-resumes when focus changes)
  Ctrl+Alt+Q : quit from anywhere
  o          : (in preview window) manual global blur on/off
  q          : (in preview window) quit
"""
import ctypes
import re
import sys
import time
import threading

import cv2
import mss
import numpy as np
from rapidocr_onnxruntime import RapidOCR

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # correct pixel coords on scaled displays
except Exception:
    pass

try:
    import win32gui  # Windows only, used for per-window opt-out
except ImportError:
    win32gui = None

try:
    import keyboard  # global hotkey
except ImportError:
    keyboard = None

WINDOW = "SnapGuard - outgoing shared feed"
EXCLUDE_SELF = "--record" not in sys.argv   # hide preview from our own capture (no hall of mirrors)

SCALE = 0.75         # OCR runs on a downscaled frame for speed (1.0 = most accurate)
PIXEL_BLOCK = 10     # bigger = more anonymised
PAD = 6              # padding around detected text box (px)
PREVIEW_W = 800

PATTERNS = {
    "email": r"[\w.+-]+@[\w-]+\.[\w.-]+",
    "phone": r"(?:\+?91[\s-]?)?[6-9]\d{9}\b",
    "api_key": r"\b(?:sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|AIza[0-9A-Za-z_-]{30,})\b",
    "secret_assign": r"(?i)(api[_-]?key|secret|token|password|passwd)\s*[:=]\s*\S+",
    "long_token": r"\b[A-Za-z0-9_\-]{32,}\b",
    "aadhaar": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
    "card": r"\b(?:\d[ -]?){13,16}\b",
}
COMPILED = {name: re.compile(p) for name, p in PATTERNS.items()}


def classify(text):
    return [name for name, rx in COMPILED.items() if rx.search(text)]


class Detector(threading.Thread):
    """Runs OCR in the background so the preview never stalls."""

    def __init__(self):
        super().__init__(daemon=True)
        self.ocr = RapidOCR()
        self.lock = threading.Lock()
        self.pending = None
        self.boxes = []      # (x0, y0, x1, y1, labels) in full-res coords
        self.latency_ms = 0
        self.running = True
        self._last = None

    def submit(self, frame):
        with self.lock:
            self.pending = frame

    def run(self):
        while self.running:
            with self.lock:
                frame, self.pending = self.pending, None
            if frame is None:
                time.sleep(0.01)
                continue
            try:
                t0 = time.time()
                small = cv2.resize(frame, None, fx=SCALE, fy=SCALE)
                result, _ = self.ocr(small)
                result = result or []
                boxes = []
                for box, text, _score in result:
                    labels = classify(text)
                    if labels:
                        pts = np.array(box, dtype=float) / SCALE
                        x0, y0 = pts.min(axis=0).astype(int)
                        x1, y1 = pts.max(axis=0).astype(int)
                        boxes.append((x0, y0, x1, y1, labels))
                self.boxes = boxes
                self.latency_ms = int((time.time() - t0) * 1000)
                summary = (len(result), len(boxes))
                if summary != self._last:   # debug: only print when something changes
                    print(f"[OCR] {len(result)} text lines read, {len(boxes)} sensitive, {self.latency_ms} ms")
                    self._last = summary
            except Exception as e:
                print("[OCR ERROR]", repr(e))
                time.sleep(0.5)


def pixelate(img, x0, y0, x1, y1):
    h, w = img.shape[:2]
    x0, y0 = max(0, x0 - PAD), max(0, y0 - PAD)
    x1, y1 = min(w, x1 + PAD), min(h, y1 + PAD)
    if x1 <= x0 or y1 <= y0:
        return
    roi = img[y0:y1, x0:x1]
    sw = max(1, (x1 - x0) // PIXEL_BLOCK)
    sh = max(1, (y1 - y0) // PIXEL_BLOCK)
    tiny = cv2.resize(roi, (sw, sh), interpolation=cv2.INTER_LINEAR)
    img[y0:y1, x0:x1] = cv2.resize(tiny, (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST)


def exclude_from_capture():
    """Hide our preview window from screen capture (Windows 10 2004+). Kills the hall of mirrors."""
    try:
        hwnd = ctypes.windll.user32.FindWindowW(None, WINDOW)
        if hwnd:
            return bool(ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x11))
    except Exception:
        pass
    return False


def main():
    det = Detector()
    det.start()

    state = {"optout_hwnd": None, "global_off": False, "quit": False}

    def toggle_window_optout():
        if win32gui is None:
            state["global_off"] = not state["global_off"]
            return
        hwnd = win32gui.GetForegroundWindow()
        state["optout_hwnd"] = None if state["optout_hwnd"] == hwnd else hwnd

    if keyboard is not None:
        try:
            keyboard.add_hotkey("ctrl+alt+b", toggle_window_optout)
            keyboard.add_hotkey("ctrl+alt+q", lambda: state.update(quit=True))
        except Exception as e:
            print("Hotkeys unavailable, use keys in the preview window:", e)

    excluded = not EXCLUDE_SELF
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        while not state["quit"]:
            raw = np.ascontiguousarray(np.array(sct.grab(monitor))[:, :, :3])
            det.submit(raw)
            out = raw.copy()

            # per-window opt-out, auto-resume when focus moves elsewhere
            opted_out = state["global_off"]
            if win32gui is not None and state["optout_hwnd"] is not None:
                if win32gui.GetForegroundWindow() == state["optout_hwnd"]:
                    opted_out = True
                else:
                    state["optout_hwnd"] = None

            if not opted_out:
                for x0, y0, x1, y1, _labels in det.boxes:
                    pixelate(out, x0, y0, x1, y1)

            status = "BLUR OFF (opt-out)" if opted_out else f"PROTECTED | {len(det.boxes)} hidden"
            preview = cv2.resize(out, (PREVIEW_W, int(out.shape[0] * PREVIEW_W / out.shape[1])))
            cv2.putText(preview, f"SnapGuard | {status} | OCR {det.latency_ms} ms (on-device)",
                        (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
            cv2.imshow(WINDOW, preview)

            if not excluded:
                excluded = exclude_from_capture()

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("o"):
                state["global_off"] = not state["global_off"]

    det.running = False
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()