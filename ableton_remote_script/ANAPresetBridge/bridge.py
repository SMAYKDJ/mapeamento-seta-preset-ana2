import json
import socket

from _Framework.ControlSurface import ControlSurface

HOST, PORT = "127.0.0.1", 9877


class ANAPresetBridge(ControlSurface):
    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)
        self._sock = None
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._sock.bind((HOST, PORT))
            self._sock.setblocking(False)
            self.log_message("ANAPresetBridge: ouvindo em %s:%d" % (HOST, PORT))
        except Exception as e:
            self.log_message("ANAPresetBridge: erro ao abrir socket: %s" % e)
            self._sock = None
        self.schedule_message(1, self._poll)

    # ------------------------------------------------------------ rede
    def _poll(self):
        if self._sock is not None:
            for _ in range(20):
                try:
                    data, addr = self._sock.recvfrom(4096)
                except (BlockingIOError, socket.error):
                    break
                try:
                    reply = self._handle(json.loads(data.decode("utf-8")))
                except Exception as e:
                    reply = {"ok": False, "error": str(e)}
                try:
                    self._sock.sendto(json.dumps(reply).encode("utf-8"), addr)
                except Exception:
                    pass
        self.schedule_message(1, self._poll)

    # ------------------------------------------------------------ Live
    def _walk(self, devices, path):
        for d in devices:
            yield d, path
            for chain in getattr(d, "chains", []) or []:
                for item in self._walk(chain.devices, path + [chain.name]):
                    yield item

    def _plugins(self, match):
        song = self.song()
        sel = song.view.selected_track
        out = []
        tracks = list(song.tracks) + list(song.return_tracks)
        for t in tracks:
            for d, _ in self._walk(t.devices, []):
                if match.lower() in (d.name or "").lower() or match.lower() in (getattr(d, "class_display_name", "") or "").lower():
                    out.append((t, d))
        # prioridade: faixa selecionada
        out.sort(key=lambda td: 0 if td[0] == sel else 1)
        return out

    def _info(self, t, d):
        presets = list(getattr(d, "presets", []) or [])
        idx = getattr(d, "selected_preset_index", -1)
        return {"track": t.name, "device": d.name, "class": d.class_name,
                "presets": len(presets),
                "current": presets[idx] if 0 <= idx < len(presets) else None,
                "index": idx}

    def _handle(self, msg):
        cmd = msg.get("cmd")
        match = msg.get("match") or "ANA"
        found = self._plugins(match)
        if cmd == "status":
            return {"ok": True, "devices": [self._info(t, d) for t, d in found]}
        if cmd == "step":
            for t, d in found:
                presets = list(getattr(d, "presets", []) or [])
                if len(presets) > 1:
                    n = len(presets)
                    idx = (getattr(d, "selected_preset_index", 0) + int(msg.get("dir", 1))) % n
                    d.selected_preset_index = idx
                    return {"ok": True, "name": presets[idx], "index": idx, "total": n,
                            "track": t.name}
            return {"ok": False, "error": "nenhum plugin com lista de presets",
                    "devices": [self._info(t, d) for t, d in found]}
        return {"ok": False, "error": "comando desconhecido"}

    def disconnect(self):
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
        ControlSurface.disconnect(self)
