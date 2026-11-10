# Firmware (ESP32)

Not written yet. This is the client side of the protocol defined in
`pc/protocolo.py`.

## Planned

- WebSocket client connecting to the address `main.py` prints on startup
- RC522 reader on SPI, sending `{"tipo": "rfid", "uid": "..."}`
- GC9A01 round display rendering the states the server sends back
- Buzzer for the beep vocabulary
- Servos for the antennas and body rotation

## Hardware notes to not relearn the hard way

- **RC522 is 3.3 V only.** 5 V kills it.
- **GPIO 6–11 are wired to the internal flash** on most ESP32 boards. Using
  them bricks the boot.
- **GPIO 34–39 are input only** — no output, no internal pull-ups.
- **GPIO 12 is a strapping pin**; a pull-up at boot changes the flash voltage.
- **Servos need their own supply.** Their inrush current browns out the ESP32,
  and the symptom looks exactly like a software bug.
- Call `detach()` on an idle servo or it buzzes continuously.
