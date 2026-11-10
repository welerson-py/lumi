# Lumi

A distributed desk assistant: an embedded ESP32 client and a Python server,
talking over WebSocket, with a local language model doing the thinking and a
deliberately narrow blast radius.

The robot never sends a command. It sends the **name** of an action, which the
server resolves against a hand-written registry. Nothing arriving over the
network can become a system command.

---

## Why that rule exists

This is not paranoia about a desk toy. The finished system has a microphone
that is always on, sits on the local network, and can open programs and switch
on power sockets. The UID of a common RFID card is cloneable with a phone, and
any device on the same network can open a socket and send an invented message.

So the boundary is drawn once, at the protocol:

```
robot  ──"foco"──▶  server  ──▶  lookup in acoes.py  ──▶  run or refuse
                                 (closed dict, written by hand)
```

A name that isn't in the registry does nothing and logs a warning. There is no
code path where network text reaches a shell. When the LLM stage lands, the
model's only power is to **pick a name from that list** — it never composes a
command either.

## Architecture

```
┌─────────────────┐                      ┌──────────────────────────────┐
│   ESP32         │   WebSocket (JSON)   │   PC (Python, asyncio)        │
│                 │ ───────────────────▶ │                               │
│  RFID RC522     │   {"tipo":"rfid",    │   servidor.py   transport     │
│  GC9A01 display │    "uid":"04A1B2C3"} │   protocolo.py  vocabulary    │
│  distance, buzz │                      │   perfis.py     card → mode   │
│  servos         │ ◀─────────────────── │   acoes.py      closed registry│
└─────────────────┘   {"tipo":"estado",  │   main.py       the glue      │
                       "estado":"FOCO"}  └──────────────────────────────┘
```

| File | Responsibility | What it does *not* do |
|---|---|---|
| `protocolo.py` | shared vocabulary: message types, states, gestures, UID normalisation | knows nothing about networking or profiles |
| `servidor.py` | transport: accept the connection, validate shape, hand off | decides nothing |
| `perfis.py` + `perfis.toml` | which card activates which mode | executes nothing |
| `acoes.py` | the closed list of what may happen on the PC | never receives text from the network |
| `main.py` | glue: event → profile → actions → face and speech | doesn't know how WebSocket works |
| `simular.py` | a fake ESP32 for development | — |

Each piece is replaceable without touching the others.

## Running it without any hardware

`simular.py` opens a real WebSocket connection and sends the real JSON, so the
whole PC side can be developed and tested before a single component is wired.

```bash
pip install -r pc/requirements.txt

python pc/main.py                      # terminal 1 — waits for the robot
python pc/simular.py rfid 04A1B2C3     # terminal 2 — "taps" a card
python pc/simular.py                   # or interactive: type a UID, press enter
```

On startup `main.py` prints the LAN address to flash into the ESP32 firmware
(`ws://192.168.x.x:8765`).

Cards already registered: `04A1B2C3` (computing), `04D4E5F6` (recipes),
`049A8B7C` (study), `04FFEEDD` (rest).

## Design notes worth reading the code for

**Per-connection state.** Each WebSocket connection gets its own `Ligacao`
object bound to one socket. Without it, a slow coroutine from a dead connection
could deliver its late message into the next session — a bug that is easy to
write and miserable to observe.

**Actions report honestly.** `acoes.py` checks that a path exists before
claiming success. The system command runs in another process, so its failure
never comes back on its own; without that check an action says "ok" while
nothing opens.

**Profiles load inside `main()`, not at import.** A malformed `perfis.toml`
should surface as a log line, not a raw traceback before logging exists.

## Status

- [x] PC side: protocol, server, profiles, action registry, simulator
- [ ] ESP32 firmware: WebSocket client, RC522, GC9A01, buzzer, servos
- [ ] Voice: INMP441 over I2S → local transcription → MAX98357 playback
- [ ] LLM stage: local model picking action names, one persona per profile

## Stack

Python 3.11+ · asyncio · websockets · tomllib · ESP32 · RC522 · GC9A01

## A note on smart plugs

Most cheap Wi-Fi sockets (Tuya, Smart Life and the market brands on the same
chip) only obey through the manufacturer's cloud: a card tap on the desk would
reach a server on the other side of the world to light a lamp two metres away,
and stop working when the internet drops. For genuine local control:
**Shelly** (documented local HTTP API), anything running **Tasmota**, or
**Home Assistant** as a single layer in front of everything.

## Licence

MIT. See [LICENSE](LICENSE).

Code comments and `docs/LEIAME.md` are in Brazilian Portuguese.
