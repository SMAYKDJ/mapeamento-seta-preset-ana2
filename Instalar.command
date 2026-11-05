#!/bin/zsh
# Instala o ANA Preset Knob: liga sozinho com o Mac e abre a interface.
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
APP="$HOME/Library/Application Support/ANA Preset Knob"
LABEL="com.smaykdj.anapresetknob"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

echo "== ANA Preset Knob — instalação =="
PY=$(command -v python3 || true)
if [ -z "$PY" ]; then
  echo "Python 3 não encontrado. Instale com: brew install python  (ou https://www.python.org)"
  read -k1 "?Pressione uma tecla para sair..."; exit 1
fi

mkdir -p "$APP" "$HOME/Library/LaunchAgents"
cp "$SRC/ana_preset_agent.py" "$SRC/interface.html" "$APP/"

if [ ! -x "$APP/venv/bin/python" ]; then
  echo "Criando ambiente Python..."
  "$PY" -m venv "$APP/venv"
fi
echo "Instalando dependências..."
"$APP/venv/bin/pip" install -q --upgrade pip
"$APP/venv/bin/pip" install -q python-rtmidi pyobjc-framework-Quartz pyobjc-framework-ApplicationServices

cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array>
    <string>$APP/venv/bin/python</string>
    <string>$APP/ana_preset_agent.py</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ProcessType</key><string>Interactive</string>
  <key>StandardOutPath</key><string>$APP/agente.log</string>
  <key>StandardErrorPath</key><string>$APP/agente.log</string>
</dict></plist>
PL

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
sleep 2
open "http://127.0.0.1:8765"
echo
echo "Pronto! O ANA Preset Knob agora liga sozinho com o Mac."
echo "Interface: http://127.0.0.1:8765  (ou dois cliques em 'Abrir interface.command')"
echo "Na primeira vez, o macOS vai pedir permissões (Acessibilidade e controle do"
echo "System Events) para o Python — aceite as duas."
