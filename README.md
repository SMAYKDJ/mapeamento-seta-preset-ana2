# Mapeamento da seta de preset — ANA 2

Troque os presets do sintetizador **ANA 2 (Sonic Academy)** girando um knob do seu controlador MIDI no Ableton Live.

O ANA 2 **não aceita Program Change nem mapeamento MIDI das setas de preset** ([confirmado pelo suporte](https://forums.sonicacademy.com/t/does-anyone-know-if-i-can-change-a-preset-with-my-midi-controller/36226)). Este script contorna isso: ele escuta o knob e clica nas setas ◀ ▶ da janela do plugin.

Testado com **Akai APC Key 25 mk2** (knob 1 = CC 48, relativo) no macOS + Ableton Live 12.

## Instalação (macOS)

```bash
python3 -m venv ~/ana-knob-env
source ~/ana-knob-env/bin/activate
pip install -r requirements.txt
```

Em **Ajustes do Sistema → Privacidade e Segurança → Acessibilidade**, ative o **Terminal**.

## Uso

1. No Ableton, abra a janela do ANA 2 (chave inglesa no device).
2. Calibre uma vez (opcional se a escala da interface for 100%):
   ```bash
   python ana_knob.py --calibrate
   ```
   Fique no Ableton e pouse o mouse sobre ◀ e depois ▶ durante as contagens.
3. Rode:
   ```bash
   python ana_knob.py
   ```
   Ou dê dois cliques em `ANA Knob.command`.

### Opções

| Opção | Efeito |
|---|---|
| `--learn` | mostra os CCs que chegam (descobrir o knob) |
| `--cc 49` | usar outro knob |
| `--mode absolute` | controladores com knob absoluto (0–127) |
| `--step 3` | girar mais para trocar de preset |
| `--interval 250` | mais tempo para presets pesados carregarem |
| `--save` | salva as opções em `~/.ana_knob.json` |

`midi_diag.py` lista as portas MIDI e mostra tudo que chega, útil para outros controladores.

## Observações

- O Ableton esconde janelas de plugin quando ele não está em primeiro plano; o script só clica com a janela do ANA visível.
- A APC Key 25 mk2 envia os knobs pela porta **Control** e em modo **relativo** (1 = direita, 127 = esquerda).
