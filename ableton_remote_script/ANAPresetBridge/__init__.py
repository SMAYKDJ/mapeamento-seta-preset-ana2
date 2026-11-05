# ANA Preset Bridge — Remote Script do Ableton Live.
# Recebe comandos do agente "ANA Preset Knob" por UDP (127.0.0.1:9877) e troca
# o preset do plugin pela API do próprio Live (PluginDevice.presets /
# selected_preset_index), sem precisar da janela do plugin.
from .bridge import ANAPresetBridge


def create_instance(c_instance):
    return ANAPresetBridge(c_instance)
