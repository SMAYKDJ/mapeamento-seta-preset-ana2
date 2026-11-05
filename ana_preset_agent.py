#!/usr/bin/env python3
"""
ANA Preset Knob — agente em segundo plano.

Troca os presets do ANA 2 (Sonic Academy) com qualquer knob ou pad de
qualquer controlador MIDI, clicando nas setas ◀ ▶ da janela do plugin.

- Abre automaticamente todas as portas MIDI e reconhece equipamentos
  conectados depois (varre a cada 2 s).
- Modo "Aprender": gire um knob ou aperte um pad e ele é mapeado.
- Interface com instruções em http://127.0.0.1:8765

Requisitos: python-rtmidi, pyobjc-framework-Quartz (macOS).
"""

import json
import queue
from collections import deque
from urllib.parse import urlparse, parse_qs
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    import rtmidi
except ImportError:
    sys.exit("Falta o rtmidi: pip install python-rtmidi")
try:
    import Quartz
except ImportError:
    sys.exit("Falta o Quartz: pip install pyobjc-framework-Quartz")

APP_NAME = "ANA Preset Knob"
HOST, PORT = "127.0.0.1", 8765
HERE = Path(__file__).resolve().parent
CONFIG_PATH = Path.home() / ".ana_knob.json"

DEFAULTS = {
    "window_match": "ANA 2",
    "step": 20,              # cliques de knob por preset
    "interval_ms": 150,      # tempo mínimo entre cliques nas setas
    "max_pending": 2,
    "restore_mouse": True,
    "auto_focus_live": True,  # traz o Ableton para frente se a janela do ANA estiver oculta
    "return_focus": True,     # depois do clique, volta para o app em que você estava
    "ref_width": 1054.0,
    "prev": [517.0, 55.8],
    "next": [536.5, 55.8],
    # mapeamentos: knob, prev, next (cada um pode ser None)
    "bindings": {
        "knob": {"port": "APC Key 25 mk2 Control", "type": "cc", "channel": 0,
                 "number": 48, "mode": "relative"},
        "prev": None,
        "next": None,
    },
}


# ===================================================================== config

class Config:
    def __init__(self):
        self.lock = threading.RLock()
        self.data = json.loads(json.dumps(DEFAULTS))
        if CONFIG_PATH.exists():
            try:
                saved = json.loads(CONFIG_PATH.read_text())
                b = saved.pop("bindings", None)
                # compatibilidade com a versão anterior (ana_knob.py)
                old = {k: saved.pop(k, None) for k in ("cc", "channel", "mode", "port_match")}
                self.data.update({k: v for k, v in saved.items() if k in DEFAULTS})
                if b:
                    self.data["bindings"].update(b)
                elif old.get("cc") is not None:
                    self.data["bindings"]["knob"].update(
                        number=old["cc"], channel=old.get("channel") or 0,
                        mode=old.get("mode") or "relative")
            except Exception as e:
                log(f"Não consegui ler {CONFIG_PATH}: {e}")

    def get(self, k):
        with self.lock:
            return self.data[k]

    def set(self, **kw):
        with self.lock:
            self.data.update(kw)
            self.save()

    def bind(self, slot, value):
        with self.lock:
            self.data["bindings"][slot] = value
            self.save()

    def save(self):
        CONFIG_PATH.write_text(json.dumps(self.data, indent=2, ensure_ascii=False))

    def snapshot(self):
        with self.lock:
            return json.loads(json.dumps(self.data))


LOG = []


def log(msg):
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    LOG.append(line)
    del LOG[:-60]


# ===================================================================== janela / mouse

_AX_SCRIPT = '''
tell application "System Events"
    set out to ""
    repeat with p in (every process whose name starts with "Live")
        repeat with w in (every window of p)
            try
                set {px, py} to position of w
                set {sw, sh} to size of w
                set out to out & (name of w) & "\t" & px & "\t" & py & "\t" & sw & "\t" & sh & linefeed
            end try
        end repeat
    end repeat
    return out
end tell
'''
_ax_cache = {"t": 0.0, "rows": [], "error": None}


def live_windows():
    """Janelas do Ableton via Acessibilidade (não precisa de Gravação de Tela)."""
    now = time.time()
    if now - _ax_cache["t"] < 0.5:
        return _ax_cache["rows"]
    rows, err = [], None
    try:
        r = subprocess.run(["osascript", "-e", _AX_SCRIPT],
                           capture_output=True, text=True, timeout=10)
        for line in r.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) == 5:
                rows.append((parts[0], *map(float, parts[1:])))
        if r.returncode != 0:
            err = (r.stderr or "").strip()[:200]
    except Exception as e:
        err = str(e)[:200]
    _ax_cache.update(t=now, rows=rows, error=err)
    return rows


try:
    import AppKit
except ImportError:
    AppKit = None

try:
    import ApplicationServices as AS
except ImportError:
    AS = None

_DIAG = {"method": None, "live_windows": []}


def _live_quartz():
    """Janelas do Ableton (dono 'Live') visíveis na tela, via Quartz.
    Nomes só aparecem com Gravação de Tela; dono, PID e tamanho sempre."""
    opts = (Quartz.kCGWindowListOptionOnScreenOnly
            | Quartz.kCGWindowListExcludeDesktopElements)
    out = []
    for w in Quartz.CGWindowListCopyWindowInfo(opts, Quartz.kCGNullWindowID) or []:
        if (w.get("kCGWindowOwnerName") or "").startswith("Live") and w.get("kCGWindowLayer", 0) == 0:
            b = w["kCGWindowBounds"]
            out.append((w.get("kCGWindowName") or "", int(w.get("kCGWindowOwnerPID", 0)),
                        float(b["X"]), float(b["Y"]), float(b["Width"]), float(b["Height"])))
    return out


def _ax_windows(pid):
    """Títulos e posições pela API de Acessibilidade (sem System Events)."""
    if AS is None or not pid:
        return []
    rows = []
    try:
        app = AS.AXUIElementCreateApplication(pid)
        err, wins = AS.AXUIElementCopyAttributeValue(app, AS.kAXWindowsAttribute, None)
        for win in (wins or []) if err == 0 else []:
            _, title = AS.AXUIElementCopyAttributeValue(win, AS.kAXTitleAttribute, None)
            _, pos = AS.AXUIElementCopyAttributeValue(win, AS.kAXPositionAttribute, None)
            _, size = AS.AXUIElementCopyAttributeValue(win, AS.kAXSizeAttribute, None)
            ok1, p = AS.AXValueGetValue(pos, AS.kAXValueCGPointType, None)
            ok2, sz = AS.AXValueGetValue(size, AS.kAXValueCGSizeType, None)
            if ok1 and ok2:
                rows.append((str(title or ""), p.x, p.y, sz.width, sz.height))
    except Exception as e:
        _DIAG["ax_exception"] = str(e)[:200]
    return rows


def find_window(match):
    q = _live_quartz()
    # 1) Quartz com nome (precisa de Gravação de Tela)
    for name, _pid, x, y, w, h in q:
        if match in name:
            _DIAG.update(method="quartz", live_windows=[r[0] for r in q])
            return x, y, w, h
    # 2) Acessibilidade nativa (precisa só de Acessibilidade)
    pids = {r[1] for r in q}
    if not pids:
        try:
            out = subprocess.run(["pgrep", "-x", "Live"], capture_output=True, text=True).stdout
            pids = {int(p) for p in out.split()}
        except Exception:
            pass
    for pid in pids:
        rows = _ax_windows(pid)
        if rows:
            _DIAG["live_windows"] = [r[0] for r in rows]
        for name, x, y, w, h in rows:
            if match in name:
                _DIAG["method"] = "acessibilidade"
                return x, y, w, h
    # 3) System Events (osascript)
    for name, x, y, w, h in live_windows():
        if match in name:
            _DIAG["method"] = "system events"
            return x, y, w, h
    # 4) Sem nomes: janela do Live que não é a principal e tem a proporção do ANA
    if q and not any(r[0] for r in q):
        main = max(q, key=lambda r: r[4] * r[5])
        ref = 1054.0 / 804.0
        cands = [r for r in q if r is not main and 500 < r[4] < 2400
                 and abs(r[4] / max(r[5], 1) - ref) < 0.12]
        if len(cands) == 1:
            _DIAG["method"] = "tamanho"
            _, _, x, y, w, h = cands[0]
            return x, y, w, h
    _DIAG["method"] = None
    return None


def frontmost_app():
    if AppKit is None:
        return None
    try:
        return AppKit.NSWorkspace.sharedWorkspace().frontmostApplication()
    except Exception:
        return None


def live_app():
    if AppKit is None:
        return None
    for app in AppKit.NSWorkspace.sharedWorkspace().runningApplications():
        bid = app.bundleIdentifier() or ""
        if bid.startswith("com.ableton.live"):
            return app
    return None


def activate(app):
    try:
        app.activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps)
        return True
    except Exception:
        return False


def mouse_pos():
    p = Quartz.CGEventGetLocation(Quartz.CGEventCreate(None))
    return p.x, p.y


def click_at(x, y, restore=True):
    orig = mouse_pos()
    pt = Quartz.CGPointMake(x, y)
    for et in (Quartz.kCGEventMouseMoved, Quartz.kCGEventLeftMouseDown,
               Quartz.kCGEventLeftMouseUp):
        ev = Quartz.CGEventCreateMouseEvent(None, et, pt, Quartz.kCGMouseButtonLeft)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
        time.sleep(0.012)
    if restore:
        Quartz.CGWarpMouseCursorPosition(Quartz.CGPointMake(*orig))
        Quartz.CGAssociateMouseAndMouseCursorPosition(True)


def can_click():
    try:
        return bool(Quartz.CGPreflightPostEventAccess())
    except Exception:
        return None


def request_click_permission():
    try:
        Quartz.CGRequestPostEventAccess()
    except Exception:
        pass
    subprocess.run(["open", "x-apple.systempreferences:com.apple.preference.security"
                    "?Privacy_Accessibility"])


# ===================================================================== MIDI

def decode(msg):
    """bytes -> (type, channel, number, value) ou None."""
    if len(msg) < 3:
        return None
    st, d1, d2 = msg[0], msg[1], msg[2]
    kind, ch = st & 0xF0, st & 0x0F
    if kind == 0xB0:
        return ("cc", ch, d1, d2)
    if kind == 0x90:
        return ("note", ch, d1, d2)          # velocity 0 = note off
    if kind == 0x80:
        return ("note", ch, d1, 0)
    return None


def describe(b):
    if not b:
        return "—"
    t = "CC" if b["type"] == "cc" else "Nota"
    extra = f" · {'relativo' if b.get('mode') == 'relative' else 'absoluto'}" if "mode" in b else ""
    return f"{t} {b['number']} · canal {b['channel'] + 1} · {b['port']}{extra}"


class MidiHub:
    """Mantém todas as portas de entrada abertas; reconecta ao plugar."""

    def __init__(self):
        self.q = queue.Queue()
        self.open = {}          # nome -> MidiIn
        self.lock = threading.Lock()

    def scan(self):
        try:
            names = rtmidi.MidiIn().get_ports()
        except Exception as e:
            log(f"Erro ao listar portas MIDI: {e}")
            return
        with self.lock:
            for gone in [n for n in self.open if n not in names]:
                try:
                    self.open.pop(gone).close_port()
                except Exception:
                    pass
                log(f"Desconectado: {gone}")
            for i, n in enumerate(names):
                if n in self.open:
                    continue
                try:
                    m = rtmidi.MidiIn()
                    m.ignore_types(sysex=True, timing=True, active_sense=True)
                    m.set_callback(lambda ev, _d, name=n: self.q.put((name, ev[0], time.time())))
                    m.open_port(i)
                    self.open[n] = m
                    log(f"Conectado: {n}")
                except Exception as e:
                    log(f"Não consegui abrir {n}: {e}")

    def ports(self):
        with self.lock:
            return list(self.open)

    def loop(self):
        while True:
            self.scan()
            time.sleep(2)


# ===================================================================== núcleo

class Engine:
    def __init__(self, cfg, hub):
        self.cfg, self.hub = cfg, hub
        self.pending = 0
        self.acc = 0
        self.last_abs = None
        self.lock = threading.Lock()
        self.learn = None            # "knob" | "prev" | "next"
        self.learn_buf = []
        self.last_msg = None
        self.calib = {"state": "idle", "count": 0, "target": None}
        self.window_seen = None
        self.events = deque(maxlen=300)   # para a interface acender os controles
        self.seq = 0

    # ---------- entrada MIDI
    def midi_loop(self):
        while True:
            port, raw, ts = self.hub.q.get()
            d = decode(raw)
            if not d:
                continue
            t, ch, num, val = d
            self.last_msg = {"port": port, "type": t, "channel": ch, "number": num,
                             "value": val, "t": ts}
            self.seq += 1
            self.events.append({"seq": self.seq, "port": port, "type": t, "channel": ch,
                                "number": num, "value": val})
            if self.learn:
                self.handle_learn(port, t, ch, num, val, ts)
                continue
            self.dispatch(port, t, ch, num, val)

    def match(self, b, port, t, ch, num):
        return b and b["port"] == port and b["type"] == t and b["channel"] == ch and b["number"] == num

    def dispatch(self, port, t, ch, num, val):
        b = self.cfg.get("bindings")
        if self.match(b.get("prev"), port, t, ch, num):
            if val > 0:
                self.push(-1, reset=True, source="prev")
            return
        if self.match(b.get("next"), port, t, ch, num):
            if val > 0:
                self.push(+1, reset=True, source="next")
            return
        k = b.get("knob")
        if self.match(k, port, t, ch, num):
            self.knob(val, k.get("mode", "relative"))

    def knob(self, val, mode):
        if mode == "relative":
            delta = 1 if 0 < val < 64 else (-1 if val > 64 else 0)
        else:
            if self.last_abs is None:
                self.last_abs = val
                return
            delta, self.last_abs = val - self.last_abs, val
        if not delta:
            return
        if self.acc and (delta > 0) != (self.acc > 0):
            self.acc = 0
        self.acc += delta
        step = max(1, int(self.cfg.get("step")))
        steps = int(self.acc / step)
        if steps:
            self.acc -= steps * step
            self.push(steps, source="knob")

    def push(self, steps, reset=False, source=None):
        # avisa a interface (animação da função executada)
        self.seq += 1
        self.events.append({"seq": self.seq, "type": "action", "dir": 1 if steps > 0 else -1,
                            "count": abs(steps), "source": source or "virtual",
                            "port": "", "channel": 0, "number": 0, "value": 0})
        cap = int(self.cfg.get("max_pending"))
        with self.lock:
            if reset and self.pending and (steps > 0) != (self.pending > 0):
                self.pending = 0
            self.pending = max(-cap, min(cap, self.pending + steps))

    # ---------- aprender
    def start_learn(self, slot):
        self.learn, self.learn_buf = slot, []
        log(f"Aprendendo: {slot}")

    def handle_learn(self, port, t, ch, num, val, ts):
        slot = self.learn
        if slot in ("prev", "next"):
            if val == 0:                      # ignora soltar / note off
                return
            self.cfg.bind(slot, {"port": port, "type": t, "channel": ch, "number": num})
            log(f"{'◀ Anterior' if slot == 'prev' else '▶ Próximo'} = {describe(self.cfg.get('bindings')[slot])}")
            self.learn = None
            return
        # knob: só CC; junta ~0,8 s de mensagens para detectar relativo/absoluto
        if t != "cc":
            return
        self.learn_buf.append((port, ch, num, val, ts))
        first = self.learn_buf[0]
        same = [m for m in self.learn_buf if m[:3] == first[:3]]
        if ts - first[4] < 0.8 and len(same) < 12:
            return
        vals = [m[3] for m in same]
        relative = all(v < 16 or v > 112 for v in vals)
        mode = "relative" if relative else "absolute"
        self.cfg.bind("knob", {"port": first[0], "type": "cc", "channel": first[1],
                               "number": first[2], "mode": mode})
        self.acc, self.last_abs, self.learn = 0, None, None
        log(f"Knob = {describe(self.cfg.get('bindings')['knob'])}")

    # ---------- cliques
    def click_loop(self):
        warned = False
        while True:
            with self.lock:
                p = self.pending
            if not p:
                ra = getattr(self, "return_app", None)
                if ra is not None and time.time() > self.return_at:
                    self.return_app = None
                    activate(ra)
                time.sleep(0.005)
                continue
            win = find_window(self.cfg.get("window_match"))
            back_to = None
            if not win and self.cfg.get("auto_focus_live"):
                # O Live esconde janelas de plugin quando não está na frente:
                # traz o Ableton, espera a janela do ANA reaparecer, clica e volta.
                live, front = live_app(), frontmost_app()
                if live is not None and activate(live):
                    if front is not None and front.bundleIdentifier() != live.bundleIdentifier():
                        back_to = front
                    for _ in range(25):
                        time.sleep(0.04)
                        _ax_cache["t"] = 0
                        win = find_window(self.cfg.get("window_match"))
                        if win:
                            time.sleep(0.06)
                            break
            if not win:
                if not warned:
                    log("Janela do ANA 2 não está aberta — clique na chave inglesa do device no Ableton.")
                    warned = True
                with self.lock:
                    self.pending = 0
                if back_to is not None:
                    activate(back_to)
                continue
            warned = False
            # executa tudo o que estiver na fila enquanto o Ableton está na frente
            while True:
                with self.lock:
                    p = self.pending
                if not p:
                    break
                direction = 1 if p > 0 else -1
                self.arrow(direction, win)
                with self.lock:
                    self.pending -= direction
                time.sleep(self.cfg.get("interval_ms") / 1000.0)
                win = find_window(self.cfg.get("window_match")) or win
            if self.cfg.get("return_focus"):
                if back_to is not None and getattr(self, "return_app", None) is None:
                    self.return_app = back_to
                if getattr(self, "return_app", None) is not None:
                    self.return_at = time.time() + 0.7   # volta após 0,7 s sem toques

    def arrow(self, direction, win=None):
        win = win or find_window(self.cfg.get("window_match"))
        if not win:
            return False
        x, y, w, _ = win
        ref = float(self.cfg.get("ref_width")) or w
        ox, oy = self.cfg.get("next" if direction > 0 else "prev")
        s = w / ref
        click_at(x + ox * s, y + oy * s, self.cfg.get("restore_mouse"))
        return True

    # ---------- calibração (contagem regressiva; o usuário fica no Ableton)
    def calibrate(self):
        def run():
            for target in ("prev", "next"):
                self.calib.update(target=target, state="counting")
                for i in range(6, 0, -1):
                    self.calib["count"] = i
                    time.sleep(1)
                win = find_window(self.cfg.get("window_match"))
                if not win:
                    self.calib.update(state="error", count=0)
                    log("Calibração: janela do ANA 2 não visível.")
                    return
                mx, my = mouse_pos()
                x, y, w, _ = win
                self.cfg.set(**{target: [round(mx - x, 1), round(my - y, 1)], "ref_width": w})
                log(f"Calibração {target}: {self.cfg.get(target)}")
            self.calib.update(state="done", count=0, target=None)
        threading.Thread(target=run, daemon=True).start()

    # ---------- estado para a interface
    def state(self, since=None):
        c = self.cfg.snapshot()
        now = time.time()
        if now - getattr(self, "_win_t", 0) > 1.0:      # não varre janelas a cada poll
            self._win, self._win_t = bool(find_window(c["window_match"])), now
        win = self._win
        lm = self.last_msg
        return {
            "ports": self.hub.ports(),
            "bindings": {k: {"raw": v, "text": describe(v)} for k, v in c["bindings"].items()},
            "learn": self.learn,
            "last": (f"{'CC' if lm['type'] == 'cc' else 'Nota'} {lm['number']} = {lm['value']} "
                     f"(canal {lm['channel'] + 1}) · {lm['port']}") if lm and time.time() - lm["t"] < 5 else None,
            "window": bool(win),
            "windows": _DIAG.get("live_windows") or [r[0] for r in _ax_cache["rows"]],
            "find_method": _DIAG.get("method"),
            "ax_exception": _DIAG.get("ax_exception"),
            "ax_error": _ax_cache["error"],
            "can_click": can_click(),
            "step": c["step"],
            "interval_ms": c["interval_ms"],
            "calib": self.calib,
            "log": LOG[-15:],
            "seq": self.seq,
            "acc": self.acc,
            "events": [e for e in list(self.events) if since is not None and e["seq"] > since][-60:],
        }


# ===================================================================== HTTP

class Handler(BaseHTTPRequestHandler):
    engine = None

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            return self._send(200, (HERE / "interface.html").read_bytes(), "text/html")
        if u.path == "/classic" and (HERE / "interface_classic.html").exists():
            return self._send(200, (HERE / "interface_classic.html").read_bytes(), "text/html")
        static = {"/vendor/three.module.min.js": "vendor/three.module.min.js",
                  "/vendor/OrbitControls.js": "vendor/OrbitControls.js",
                  "/controller3d.js": "controller3d.js",
                  "/controller3d_classic.js": "controller3d_classic.js"}
        if u.path in static and (HERE / static[u.path]).exists():
            return self._send(200, (HERE / static[u.path]).read_bytes(), "text/javascript")
        if u.path == "/api/state":
            q = parse_qs(u.query)
            since = int(q["since"][0]) if q.get("since", [""])[0].lstrip("-").isdigit() else None
            return self._send(200, self.engine.state(since))
        self._send(404, {"error": "não encontrado"})

    def do_POST(self):
        # só aceita requisições da própria página (evita sites externos)
        origin = self.headers.get("Origin")
        if origin and origin not in (f"http://{HOST}:{PORT}", f"http://localhost:{PORT}"):
            return self._send(403, {"error": "origem não permitida"})
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            body = {}
        e = self.engine
        p = self.path
        if p == "/api/learn" and body.get("slot") in ("knob", "prev", "next"):
            e.start_learn(body["slot"])
        elif p == "/api/cancel":
            e.learn = None
        elif p == "/api/clear" and body.get("slot") in ("knob", "prev", "next"):
            e.cfg.bind(body["slot"], None)
        elif p == "/api/settings":
            kw = {}
            if "step" in body:
                kw["step"] = max(1, min(64, int(body["step"])))
            if "interval_ms" in body:
                kw["interval_ms"] = max(50, min(1000, int(body["interval_ms"])))
            e.cfg.set(**kw)
        elif p == "/api/test" and body.get("dir") in (-1, 1):
            e.push(body["dir"], reset=True, source=body.get("source") or "virtual")
        elif p == "/api/calibrate":
            e.calibrate()
        elif p == "/api/permission":
            request_click_permission()
        else:
            return self._send(400, {"error": "requisição inválida"})
        self._send(200, {"ok": True})


# ===================================================================== main

def main():
    cfg = Config()
    hub = MidiHub()
    eng = Engine(cfg, hub)
    Handler.engine = eng
    try:
        srv = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError:
        log(f"{APP_NAME} já está rodando — abrindo a interface.")
        webbrowser.open(f"http://{HOST}:{PORT}")
        return
    hub.scan()
    for fn in (hub.loop, eng.midi_loop, eng.click_loop):
        threading.Thread(target=fn, daemon=True).start()
    log(f"{APP_NAME} rodando. Interface: http://{HOST}:{PORT}")
    if "--open" in sys.argv:
        webbrowser.open(f"http://{HOST}:{PORT}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
