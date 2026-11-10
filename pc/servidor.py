"""Servidor WebSocket: o ponto de encontro entre o robô e o PC.

INVERSÃO EM RELAÇÃO AO ESCOPO ANTERIOR: antes o PC mandava comandos e o ESP32
era um servidor HTTP. Agora que o robô produz eventos — cartão encostado, botão,
áudio —, quem espera conexão é o PC, e o ESP32 conecta como cliente.

Isso resolve dois problemas de uma vez. Primeiro, a conexão fica aberta: um
cartão encostado chega ao PC em milissegundos, sem o robô abrir uma conexão
nova a cada leitura. Segundo, quem precisa saber um endereço passa a ser o
robô, e o endereço do PC muda menos que o do ESP32 — que é desligado e religado
toda hora enquanto você mexe nele.

O servidor não decide nada. Ele recebe, valida o formato e entrega ao
manipulador. Toda a lógica de "cartão X liga o modo Y" está em main.py.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Awaitable, Callable

import websockets
from websockets.asyncio.server import ServerConnection, serve

import protocolo
from protocolo import Mensagem

log = logging.getLogger("servidor")

Manipulador = Callable[[Mensagem, "Ligacao"], Awaitable[None]]


class Ligacao:
    """Uma conexão com o robô. Também é por aqui que o PC manda comandos.

    Cada conexão ganha a sua própria Ligacao, amarrada a um socket só. Isso
    evita um erro chato de ver e fácil de cometer: uma rotina lenta da conexão
    anterior — um `sleep` esperando para voltar o rosto ao normal, por exemplo —
    terminando depois que o robô reconectou e mandando o comando atrasado para a
    sessão nova, que já estava noutro estado.
    """

    def __init__(self, ws: ServerConnection | None = None):
        self._ws: ServerConnection | None = ws
        self.nome = "?"

    @property
    def conectado(self) -> bool:
        return self._ws is not None

    def _soltar(self) -> None:
        self._ws = None

    async def enviar_bruto(self, linha: str) -> bool:
        if self._ws is None:
            return False
        try:
            await self._ws.send(linha)
            return True
        except websockets.ConnectionClosed:
            self._ws = None
            return False

    # atalhos usados pelo resto do programa
    async def estado(self, nome: str) -> bool:
        return await self.enviar_bruto(protocolo.estado(nome))

    async def gesto(self, nome: str, **kw) -> bool:
        return await self.enviar_bruto(protocolo.gesto(nome, **kw))

    async def falar(self, texto: str) -> bool:
        return await self.enviar_bruto(protocolo.falar(texto))


class Servidor:
    def __init__(self, manipulador: Manipulador,
                 host: str = "0.0.0.0", porta: int = 8765):
        self.manipulador = manipulador
        self.host = host
        self.porta = porta
        self.ligacao = Ligacao()        # a mais recente, para envios do PC

    async def _atender(self, ws: ServerConnection) -> None:
        par = getattr(ws, "remote_address", ("?", 0))
        log.info("robô conectou de %s", par[0])
        ligacao = Ligacao(ws)
        self.ligacao = ligacao
        try:
            async for bruto in ws:
                try:
                    msg = Mensagem.de_json(bruto)
                except (json.JSONDecodeError, ValueError) as e:
                    # Não derruba a conexão por causa de uma linha torta: o
                    # firmware pode mandar lixo durante o boot, e derrubar aqui
                    # deixaria o robô num ciclo de reconexão sem explicação.
                    log.warning("mensagem inválida descartada (%s): %r", e, bruto[:120])
                    continue
                try:
                    await self.manipulador(msg, ligacao)
                except Exception as e:                      # noqa: BLE001
                    log.error("manipulador falhou em %s: %s", msg.tipo, e)
        except websockets.ConnectionClosed:
            pass
        finally:
            ligacao._soltar()
            log.info("robô desconectou")

    async def rodar(self) -> None:
        log.info("servidor ouvindo em ws://%s:%d", self.host, self.porta)
        async with serve(self._atender, self.host, self.porta,
                         ping_interval=20, ping_timeout=20):
            await asyncio.Future()      # roda até Ctrl+C
