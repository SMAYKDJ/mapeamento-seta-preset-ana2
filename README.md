# Mapeamento da seta de preset — ANA 2

Troque os presets do sintetizador **ANA 2 (Sonic Academy)** no Ableton Live com **qualquer knob ou pad** de **qualquer controlador MIDI**.

O ANA 2 não aceita Program Change nem mapeamento MIDI das setas de preset ([confirmado pelo suporte](https://forums.sonicacademy.com/t/does-anyone-know-if-i-can-change-a-preset-with-my-midi-controller/36226)). Este projeto contorna isso: um agente em segundo plano escuta seus controles e clica nas setas ◀ ▶ da janela do plugin.

## Recursos

- **Interface 3D em tela cheia** em `http://127.0.0.1:8765`: instruções e ajustes em painéis laterais recolhíveis (tecla **H**), e no modo limpo cada ação aparece animada na cena
- Versão clássica (página com rolagem) em `http://127.0.0.1:8765/classic`
- **Aprender**: clique, gire um knob ou aperte um pad, pronto
- **Knob** (relativo/infinito ou absoluto, detectado sozinho) e/ou **dois pads/botões** (◀ e ▶, um preset por toque)
- **Sensibilidade** ajustável (cliques de knob por preset)
- **Liga com o Mac** e **reconhece o controlador ao conectar**, sem reconfigurar
- Calibração das setas por contagem regressiva

## Instalação (macOS)

1. Baixe este repositório (Code → Download ZIP) e descompacte.
2. Dois cliques em **`Instalar.command`**.
   (Se o macOS bloquear: botão direito → Abrir → Abrir.)
3. A interface abre no navegador. Na primeira vez, aceite os pedidos de permissão do macOS:
   - **Acessibilidade** para o **Python** (para clicar nas setas)
   - **Controlar “System Events”** (para encontrar a janela do ANA 2)

Para abrir a interface depois: **`Abrir interface.command`** ou `http://127.0.0.1:8765`.
Para remover: **`Desinstalar.command`**.

Requer Python 3 (`brew install python` ou python.org).

## Troca 100% em segundo plano (ponte do Ableton)

O instalador também copia um *Remote Script* (`ANAPresetBridge`) para a User Library do Ableton. Com ele ativo, o preset é trocado pela API do próprio Live — sem janela, sem clique e sem tirar você do app em que está.

1. Reinicie o Ableton Live.
2. **Preferências → Link, Tempo e MIDI → Superfície de controle**: escolha **ANAPresetBridge** num slot livre (Entrada/Saída: Nenhuma).
3. A interface mostra "Ponte do Ableton ativa" e a tela 3D passa a exibir o **nome do preset**.

Funciona se a versão do ANA 2 no set publicar a lista de presets para o Live; se não publicar, a interface avisa e o agente continua usando o clique nas setas (o Ableton aparece por um instante e você volta sozinho). Se a versão VST3 não publicar, teste a versão VST2 ou AU do ANA 2.

## Uso

1. No Ableton, abra a janela do ANA 2 (chave inglesa no device).
2. Na interface, clique em **Aprender** ao lado de *Knob*, *◀ Anterior* ou *▶ Próximo* e mexa no controle.
3. Pode estar em qualquer app: se a janela do ANA estiver oculta, o agente traz o Ableton para frente, troca o preset e volta para onde você estava. A janela do plugin só precisa estar aberta (chave inglesa).

Se o seu controlador também comanda o Ableton (Control Surface), escolha um controle que não esteja mapeado lá.

## Arquivos

| Arquivo | Para quê |
|---|---|
| `ana_preset_agent.py` | agente em segundo plano + servidor da interface |
| `interface.html` | interface com instruções |
| `controller3d.js` + `vendor/` | controlador em 3D (Three.js r160, incluído para funcionar offline) |
| `Instalar.command` / `Desinstalar.command` | instala/remove com início automático (LaunchAgent) |
| `ana_knob.py` | versão simples de linha de comando (v1) |
| `midi_diag.py` | lista portas MIDI e mostra tudo que chega |

Testado com **Akai APC Key 25 mk2** + Ableton Live 12 Suite no macOS.
