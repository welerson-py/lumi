"""Um ESP32 de mentira, que fala o protocolo de verdade.

Este é o jeito honesto de testar sem hardware: em vez de chamar a função de
tratamento direto no Python, o simulador abre uma conexão WebSocket real,
manda JSON real e imprime o que volta. O caminho exercitado é o mesmo que o
ESP32 vai usar — servidor, protocolo, perfis, ações.

A diferença importa. Um teste que chama `ao_receber()` diretamente passa
mesmo com o servidor quebrado, com o JSON malformado e com a porta errada.
Este aqui falha exatamente onde o hardware falharia, que é o ponto.

    python simular.py                      # sessão interativa
    python simular.py rfid 04A1B2C3        # manda um cartão e sai
    python simular.py rfid 11223344        # cartão não cadastrado
    python simular.py botao topo
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

import websockets

PADRAO = "ws://127.0.0.1:8765"


async def escutar(ws):
    """Imprime tudo que o PC manda para o robô."""
    try:
        async for bruto in ws:
            try:
                m = json.loads(bruto)
            except json.JSONDecodeError:
                print(f"  <- (ilegível) {bruto!r}")
                continue
            tipo = m.get("tipo")
            if tipo == "estado":
                print(f"  <- rosto: {m.get('estado')}")
            elif tipo == "gesto":
                extra = {k: v for k, v in m.items() if k not in ("tipo", "gesto")}
                print(f"  <- gesto: {m.get('gesto')} {extra if extra else ''}".rstrip())
            elif tipo == "falar":
                print(f"  <- fala:  \"{m.get('texto')}\"")
            else:
                print(f"  <- {m}")
    except websockets.ConnectionClosed:
        print("  (conexão encerrada pelo PC)")


async def enviar(ws, obj: dict):
    linha = json.dumps(obj, ensure_ascii=False)
    print(f"  -> {linha}")
    await ws.send(linha)


async def sessao(url: str, comando: list[str] | None):
    try:
        ws = await websockets.connect(url, open_timeout=4)
    except (OSError, asyncio.TimeoutError, websockets.WebSocketException) as e:
        print(f"não consegui conectar em {url} ({e.__class__.__name__}).")
        print("o main.py está rodando noutro terminal?")
        sys.exit(1)

    async with ws:
        ouvinte = asyncio.create_task(escutar(ws))
        await enviar(ws, {"tipo": "ola", "versao": 1, "nome": "hub-simulado"})
        await asyncio.sleep(0.4)

        if comando:
            tipo, *resto = comando
            if tipo == "rfid":
                uid = resto[0] if resto else "04A1B2C3"
                await enviar(ws, {"tipo": "rfid", "uid": uid})
            elif tipo == "botao":
                await enviar(ws, {"tipo": "botao", "qual": resto[0] if resto else "topo"})
            elif tipo == "erro":
                await enviar(ws, {"tipo": "erro", "mensagem": " ".join(resto) or "teste"})
            else:
                print(f"comando desconhecido: {tipo}")
            await asyncio.sleep(1.2)
        else:
            print("\ndigite um UID para 'encostar o cartão', ou 'sair'.")
            print("exemplos cadastrados: 04A1B2C3, 04D4E5F6, 049A8B7C, 04FFEEDD\n")
            laco = asyncio.get_running_loop()
            while True:
                try:
                    linha = await laco.run_in_executor(None, input, "cartão> ")
                except (EOFError, KeyboardInterrupt):
                    break
                linha = linha.strip()
                if not linha:
                    continue
                if linha.lower() in ("sair", "exit", "q"):
                    break
                await enviar(ws, {"tipo": "rfid", "uid": linha})
                await asyncio.sleep(0.8)

        ouvinte.cancel()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("comando", nargs="*", help="ex.: rfid 04A1B2C3")
    ap.add_argument("--url", default=PADRAO)
    args = ap.parse_args()
    try:
        asyncio.run(sessao(args.url, args.comando or None))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
