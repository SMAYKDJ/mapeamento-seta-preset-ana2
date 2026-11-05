#!/usr/bin/env python3
"""
ana_knob.py — Navega os presets do ANA 2 girando um knob da Akai APC Key 25.

O ANA 2 não aceita Program Change, então este script:
  1. escuta o CC do knob escolhido (padrão: knob 1 = CC 48, canal 1);
  2. detecta a direção do giro (sobe = próximo, desce = anterior);
  3. clica na seta ▶ ou ◀ da janela do ANA 2, com intervalo mínimo entre
     cliques para o plugin carregar cada preset (sem pular).

Requisitos (macOS):
  pip install python-rtmidi pyobjc-framework-Quartz

Permissões (Ajustes do Sistema > Privacidade e Segurança):
  - Acessibilidade      -> para o Terminal (ou o app que roda o script) clicar
  - Gravação de Tela    -> para ler o nome das janelas e achar o ANA 2

Uso:
  python3 ana_knob.py --learn       # mostra o MIDI que chega (descobrir CC do knob)
  python3 ana_knob.py --calibrate   # grava a posição exata das setas do ANA 2
  python3 ana_knob.py               # roda
  python3 ana_knob.py --cc 49 --step 4 --interval 200

A configuração fica salva em ~/.ana_knob.json
"""

import argparse
import queue
import subprocess
import json
import sys
import threading
import time
from pathlib import Path

try:
    import rtmidi
except ImportError:
    sys.exit("Falta o rtmidi: pip install python-rtmidi")

try:
    import Quartz
except ImportError:
    sys.exit("Falta o Quartz: pip3 install pyobjc-framework-Quartz")


CONFIG_PATH = Path.home() / ".ana_knob.json"

DEFAULTS = {
    "port_match": "APC Key 25",   # trecho do nome da porta MIDI
    "channel": 0,                 # 0 = canal MIDI 1
    "cc": 48,                     # knob 1 da APC Key 25 (knobs: CC 48..55)
    "mode": "relative",           # APC Key 25 mk2: knobs relativos (1 = direita, 127 = esquerda)
    "step": 18,                   # cliques do knob para avançar 1 preset (maior = menos sensível)
    "interval_ms": 150,           # tempo mínimo entre cliques
    "max_pending": 2,             # máximo de cliques acumulados na fila
    "window_match": "ANA 2",      # trecho do título da janela do plugin
    "restore_mouse": True,        # devolve o cursor para onde estava após clicar
    # Posição das setas em pontos, relativa ao canto superior esquerdo da janela
    # (inclui a barra de título). Valores tirados da sua captura; use --calibrate
    # para gravar os exatos do seu setup.
    "ref_width": 1040.0,
    "prev": [508.5, 51.0],
    "next": [527.5, 51.0],
}


# ---------------------------------------------------------------- config

def load_config():
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text()))
        except Exception as e:
            print(f"[aviso] não consegui ler {CONFIG_PATH}: {e}")
    return cfg


def save_config(cfg):
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
    print(f"Configuração salva em {CONFIG_PATH}")


# ---------------------------------------------------------------- janela / mouse

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
_ax_cache = {"t": 0.0, "rows": []}


def _ax_windows():
    """Lista janelas do Ableton via Acessibilidade (System Events).
    Não precisa de Gravação de Tela; usa a permissão de Acessibilidade."""
    now = time.time()
    if now - _ax_cache["t"] < 0.5:
        return _ax_cache["rows"]
    rows = []
    try:
        r = subprocess.run(["osascript", "-e", _AX_SCRIPT],
                           capture_output=True, text=True, timeout=10)
        for line in r.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) == 5:
                rows.append((parts[0], *map(float, parts[1:])))
        if r.returncode != 0 and r.stderr and not _ax_cache.get("err"):
            _ax_cache["err"] = True
            print("[aviso] Acessibilidade negada para o Terminal: " + r.stderr.strip())
    except Exception as e:
        print(f"[aviso] osascript falhou: {e}")
    _ax_cache.update(t=now, rows=rows)
    return rows


def find_window(match):
    """Retorna (x, y, largura, altura) da janela cujo título contém `match`.
    Tenta primeiro pela lista do Quartz (precisa de Gravação de Tela para ver
    títulos); se não achar, cai para a Acessibilidade (System Events)."""
    opts = (Quartz.kCGWindowListOptionOnScreenOnly
            | Quartz.kCGWindowListExcludeDesktopElements)
    wins = Quartz.CGWindowListCopyWindowInfo(opts, Quartz.kCGNullWindowID) or []
    for w in wins:
        name = w.get("kCGWindowName") or ""
        if match in name:
            b = w["kCGWindowBounds"]
            return float(b["X"]), float(b["Y"]), float(b["Width"]), float(b["Height"])
    for name, x, y, w, h in _ax_windows():
        if match in name:
            return x, y, w, h
    return None


def list_live_windows():
    return [r[0] for r in _ax_windows()]


def mouse_pos():
    p = Quartz.CGEventGetLocation(Quartz.CGEventCreate(None))
    return p.x, p.y


def click_at(x, y, restore=True):
    orig = mouse_pos()
    pt = Quartz.CGPointMake(x, y)
    for etype in (Quartz.kCGEventMouseMoved,
                  Quartz.kCGEventLeftMouseDown,
                  Quartz.kCGEventLeftMouseUp):
        ev = Quartz.CGEventCreateMouseEvent(None, etype, pt, Quartz.kCGMouseButtonLeft)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
        time.sleep(0.012)
    if restore:
        Quartz.CGWarpMouseCursorPosition(Quartz.CGPointMake(*orig))
        Quartz.CGAssociateMouseAndMouseCursorPosition(True)


def arrow_point(cfg, win, which):
    x, y, w, _ = win
    scale = w / float(cfg["ref_width"]) if cfg["ref_width"] else 1.0
    ox, oy = cfg[which]
    return x + ox * scale, y + oy * scale


# ---------------------------------------------------------------- MIDI

class MidiListener:
    """Abre todas as portas que contêm `match` via rtmidi (callbacks) e
    entrega (porta, bytes) numa fila. A mk2 tem 'Keys' e 'Control';
    os knobs saem pela 'Control'."""

    def __init__(self, match):
        probe = rtmidi.MidiIn()
        names = probe.get_ports()
        found = [(i, n) for i, n in enumerate(names) if match.lower() in n.lower()]
        if not found:
            sys.exit("APC Key 25 não encontrada. Portas disponíveis:\n  "
                     + "\n  ".join(names or ["(nenhuma)"]))
        self.q = queue.Queue()
        self.ins = []
        for i, n in found:
            m = rtmidi.MidiIn()
            m.ignore_types(sysex=True, timing=True, active_sense=True)
            m.set_callback(lambda ev, _d, name=n: self.q.put((name, ev[0])))
            m.open_port(i)
            self.ins.append(m)
        self.name = " + ".join(n for _, n in found)

    def messages(self):
        while True:
            try:
                yield self.q.get(timeout=0.2)
            except queue.Empty:
                continue

    def close(self):
        for m in self.ins:
            m.close_port()


class Stepper:
    """Converte valores de CC em passos (+1 próximo / -1 anterior)."""

    def __init__(self, mode, step):
        self.mode = mode
        self.step = max(1, int(step))
        self.last = None
        self.acc = 0

    def feed(self, value):
        if self.mode == "relative":
            # só a direção importa (ignora aceleração do encoder)
            delta = 1 if 0 < value < 64 else (-1 if value > 64 else 0)
        else:
            if self.last is None:
                self.last = value
                return 0
            delta = value - self.last
            self.last = value
        if delta and self.acc and (delta > 0) != (self.acc > 0):
            self.acc = 0                       # mudou de direção: recomeça a contagem
        self.acc += delta
        steps = int(self.acc / self.step)       # trunca em direção a zero
        self.acc -= steps * self.step
        return steps


# ---------------------------------------------------------------- modos

def run_learn(cfg):
    lst = MidiListener(cfg["port_match"])
    print(f"Escutando '{lst.name}'. Gire os knobs (Ctrl+C para sair).")
    print("(notas do teclado são ignoradas aqui)")
    try:
        for name, msg in lst.messages():
            if len(msg) >= 3 and (msg[0] & 0xF0) == 0xB0:
                print(f"[{name}] CC {msg[1]:3d}  valor {msg[2]:3d}  canal {(msg[0] & 0x0F) + 1}")
    except KeyboardInterrupt:
        print("\nEncerrado.")
    finally:
        lst.close()


def _countdown(msg, secs):
    for i in range(secs, 0, -1):
        print(f"\r{msg} {i}s ", end="", flush=True)
        time.sleep(1)
    print()


def run_calibrate(cfg):
    print("CALIBRAÇÃO — o Ableton esconde a janela do plugin quando ele não está em")
    print("primeiro plano, então NÃO volte ao Terminal durante a calibração.\n")
    print("1) Clique no Ableton agora e abra a janela do ANA 2 (chave inglesa no device).")
    win = None
    deadline = time.time() + 30
    while time.time() < deadline and not win:
        win = find_window(cfg["window_match"])
        if not win:
            print(f"\r   procurando a janela do ANA 2... {int(deadline - time.time())}s ",
                  end="", flush=True)
            time.sleep(1)
    print()
    if not win:
        sys.exit("Não achei a janela do ANA 2 em 30 s. Janelas do Live vistas: "
                 f"{list_live_windows()}")
    x, y, w, h = win
    print(f"   Janela encontrada: ({x:.0f}, {y:.0f}) {w:.0f}x{h:.0f}\n")
    for key, label in (("prev", "◀ (ANTERIOR)"), ("next", "▶ (PRÓXIMO)")):
        _countdown(f"2) Pouse o mouse sobre a seta {label} do ANA e espere:", 6)
        mx, my = mouse_pos()
        win = find_window(cfg["window_match"]) or win
        x, y, w, h = win
        cfg[key] = [round(mx - x, 1), round(my - y, 1)]
        print(f"   {key} gravado: {cfg[key]}")
    cfg["ref_width"] = w
    save_config(cfg)
    print("\nCalibrado! Agora rode: python ana_knob.py")


def run(cfg):
    lst = MidiListener(cfg["port_match"])
    name = lst.name
    stepper = Stepper(cfg["mode"], cfg["step"])
    lock = threading.Lock()
    state = {"pending": 0, "stop": False, "warned": False}
    interval = cfg["interval_ms"] / 1000.0
    cap = int(cfg["max_pending"])

    def worker():
        while not state["stop"]:
            with lock:
                p = state["pending"]
            if p == 0:
                time.sleep(0.005)
                continue
            direction = 1 if p > 0 else -1
            win = find_window(cfg["window_match"])
            if win:
                state["warned"] = False
                px, py = arrow_point(cfg, win, "next" if direction > 0 else "prev")
                print(f"{'▶ próximo' if direction > 0 else '◀ anterior'}  (clique em {px:.0f},{py:.0f})")
                click_at(px, py, cfg["restore_mouse"])
                with lock:
                    state["pending"] -= direction
                time.sleep(interval)
            else:
                if not state["warned"]:
                    print("[aviso] janela do ANA 2 fechada — abra o plugin (chave inglesa no device). "
                          f"Janelas do Live vistas: {list_live_windows()}")
                    state["warned"] = True
                with lock:
                    state["pending"] = 0

    t = threading.Thread(target=worker, daemon=True)
    t.start()

    print(f"Pronto: '{name}', CC {cfg['cc']} canal {cfg['channel'] + 1}, "
          f"modo {cfg['mode']}, step {cfg['step']}, intervalo {cfg['interval_ms']} ms.")
    print("Gire o knob com a janela do ANA 2 aberta. Ctrl+C para sair.")
    try:
        for _name, msg in lst.messages():
            if (len(msg) >= 3
                    and msg[0] == (0xB0 | cfg["channel"])
                    and msg[1] == cfg["cc"]):
                steps = stepper.feed(msg[2])
                if steps:
                    with lock:
                        state["pending"] = max(-cap, min(cap, state["pending"] + steps))
    except KeyboardInterrupt:
        pass
    finally:
        state["stop"] = True
        lst.close()
        print("\nEncerrado.")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="Knob da APC Key 25 -> presets do ANA 2")
    ap.add_argument("--learn", action="store_true", help="mostra o MIDI recebido")
    ap.add_argument("--calibrate", action="store_true", help="grava a posição das setas")
    ap.add_argument("--cc", type=int, help="número do CC do knob (48..55)")
    ap.add_argument("--channel", type=int, help="canal MIDI 1..16")
    ap.add_argument("--mode", choices=["absolute", "relative"])
    ap.add_argument("--step", type=int, help="unidades de CC por preset")
    ap.add_argument("--interval", type=int, help="ms mínimos entre cliques")
    ap.add_argument("--save", action="store_true", help="salva as opções passadas")
    a = ap.parse_args()

    cfg = load_config()
    if a.cc is not None: cfg["cc"] = a.cc
    if a.channel is not None: cfg["channel"] = a.channel - 1
    if a.mode: cfg["mode"] = a.mode
    if a.step is not None: cfg["step"] = a.step
    if a.interval is not None: cfg["interval_ms"] = a.interval
    if a.save: save_config(cfg)

    if a.learn:
        run_learn(cfg)
    elif a.calibrate:
        run_calibrate(cfg)
    else:
        run(cfg)


if __name__ == "__main__":
    main()
