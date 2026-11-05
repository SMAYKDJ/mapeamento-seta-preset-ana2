#!/bin/zsh
# Clique duas vezes para gravar a posição das setas do ANA 2
source ~/ana-knob-env/bin/activate
cd "$(dirname "$0")"
python ana_knob.py --calibrate
