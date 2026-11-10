# Hub Robótico de Mesa — lado PC, etapa 1 (RFID → perfil → ação)

Esta etapa roda **inteira no computador**, sem hardware nenhum. O `simular.py`
faz o papel do ESP32: abre uma conexão WebSocket de verdade, manda o JSON de
verdade e mostra o que volta. Quando o ESP32 existir, ele entra no lugar do
simulador e nada aqui muda.

## Rodar

```
pip install -r requirements.txt

python main.py                      # terminal 1 — fica esperando o robô
python simular.py rfid 04A1B2C3     # terminal 2 — "encosta" um cartão
python simular.py                   # ou modo interativo, digita UID e enter
```

Cartões já cadastrados: `04A1B2C3` (computação), `04D4E5F6` (receitas),
`049A8B7C` (estudos), `04FFEEDD` (descanso).

O `main.py` imprime, ao subir, o endereço que vai no firmware do ESP32
(`ws://192.168.x.x:8765`).

## Os blocos

| arquivo | responsabilidade | o que NÃO faz |
|---|---|---|
| `protocolo.py` | o vocabulário das duas pontas: tipos de mensagem, estados, gestos, normalização de UID | não conhece rede nem perfis |
| `servidor.py` | transporte: aceita a conexão, valida o formato, entrega ao manipulador | não decide nada |
| `perfis.py` + `perfis.toml` | qual cartão liga qual modo | não executa nada |
| `acoes.py` | a lista fechada do que pode acontecer no PC | não recebe texto da rede |
| `main.py` | a cola: evento → perfil → ações → rosto e fala | não sabe como o WebSocket funciona |
| `simular.py` | o ESP32 de mentira | — |

Cada peça troca sem mexer nas outras. Quando entrar o LLM, ele vira mais um
bloco que **escolhe um nome** da lista de `acoes.py` — nunca monta um comando.

## Cadastrar um cartão novo

1. Encosta o cartão. No log aparece:
   `cartão não cadastrado: A1B2C3D4  (cole este UID em perfis.toml)`
2. Cola o UID na lista `cartoes` do perfil desejado, em `perfis.toml`.
3. Reinicia o `main.py`.

Um perfil aceita vários cartões (um chaveiro na mesa, outro na mochila).

## A regra de segurança

O robô manda o **nome** de uma ação; o Python procura esse nome num dicionário
escrito à mão em `acoes.py`. Nome fora da lista: nada acontece, com aviso no
log. Não existe nenhum caminho de código onde texto vindo da rede vire comando
do sistema.

Isso não é paranoia de projeto de mesa. O sistema vai ter microfone sempre
ligado, estar na rede local e ter poder de abrir programas e acionar tomadas;
o UID de um cartão comum se clona com um celular, e qualquer aparelho na mesma
rede pode abrir uma conexão e mandar mensagem inventada.

## Ações que já existem

`foco` (abre o VS Code), `estudos` (abre a pasta de estudos), `receitas`,
`navegador`, `nada`, e `luz_foco` — esta última é um espaço reservado, que hoje
só registra no log. Ajuste os caminhos em `acoes.py` para a sua máquina: a ação
avisa quando o programa não está no PATH ou a pasta não existe, em vez de dizer
que deu certo.

## Casa inteligente — aviso antes de comprar

A maioria das tomadas Wi-Fi baratas (Tuya, Smart Life e as marcas de mercado
com o mesmo chip) só obedece pela nuvem do fabricante: o cartão na mesa
acionaria um servidor do outro lado do mundo para acender uma lâmpada a dois
metros, e pararia de funcionar se a internet caísse. Com controle local de
verdade: **Shelly** (API HTTP local documentada), qualquer dispositivo com
**Tasmota**, ou **Home Assistant** como camada única na frente de tudo.

## Próximas etapas

2. Firmware do ESP32: WebSocket cliente + RC522 + OLED (os mesmos estados) +
   servos das antenas e do giro do corpo.
3. Voz: INMP441 (I2S) manda áudio para o PC, transcrição local, MAX98357 toca
   a resposta.
4. Cérebro: LLM local (Ollama) com a `persona` de cada perfil, escolhendo ações
   pelo nome.
