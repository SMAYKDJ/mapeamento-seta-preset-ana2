#!/bin/zsh
LABEL="com.smaykdj.anapresetknob"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
rm -rf "$HOME/Library/Application Support/ANA Preset Knob"
echo "ANA Preset Knob removido. (Suas configurações em ~/.ana_knob.json foram mantidas.)"
