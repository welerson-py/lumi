"""O vocabulário entre o robô e o PC. Um arquivo, duas pontas.

Toda mensagem é uma linha JSON com um campo `tipo`. Nada de formato binário
improvisado nem de string posicional: quando o firmware do ESP32 e o Python
discordarem sobre o formato — e vão discordar, em algum momento —, o erro
precisa ser legível no monitor serial.

DIREÇÃO ROBÔ → PC (eventos: coisas que aconteceram no mundo físico)
    {"tipo": "ola",    "versao": 1, "nome": "hub-mesa"}
    {"tipo": "rfid",   "uid": "04A1B2C3"}
    {"tipo": "botao",  "qual": "topo"}
    {"tipo": "erro",   "mensagem": "rc522 nao respondeu"}

DIREÇÃO PC → ROBÔ (comandos: coisas que o robô deve fazer)
    {"tipo": "estado", "estado": "PENSANDO"}
    {"tipo": "gesto",  "gesto": "girar", "para": 40}
    {"tipo": "falar",  "texto": "modo de estudos ativado"}

POR QUE VERSIONAR: o campo `versao` no "ola" existe para o dia em que o
protocolo mudar e houver um ESP32 na gaveta com firmware antigo. Sem isso, o
sintoma é um robô que conecta, não reage, e não diz por quê.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

VERSAO = 1

# Estados de rosto que o firmware sabe desenhar. Manter em sincronia com o .ino.
ESTADOS = ("DORMINDO", "OCIOSO", "OUVINDO", "PENSANDO", "FALANDO", "FELIZ", "ERRO")

# Gestos do corpo. "girar" recebe um ângulo; os outros são animações fechadas.
GESTOS = ("parado", "girar", "atencao", "comemorar", "negar")


@dataclass
class Mensagem:
    tipo: str
    dados: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def de_json(cls, linha: str | bytes) -> "Mensagem":
        if isinstance(linha, bytes):
            linha = linha.decode("utf-8", errors="replace")
        obj = json.loads(linha)
        if not isinstance(obj, dict) or "tipo" not in obj:
            raise ValueError("mensagem sem campo 'tipo'")
        tipo = obj.pop("tipo")
        return cls(tipo=str(tipo), dados=obj)

    def para_json(self) -> str:
        return json.dumps({"tipo": self.tipo, **self.dados}, ensure_ascii=False)


def estado(nome: str) -> str:
    nome = nome.upper()
    if nome not in ESTADOS:
        raise ValueError(f"estado inválido: {nome}")
    return Mensagem("estado", {"estado": nome}).para_json()


def gesto(nome: str, **kwargs) -> str:
    if nome not in GESTOS:
        raise ValueError(f"gesto inválido: {nome}")
    return Mensagem("gesto", {"gesto": nome, **kwargs}).para_json()


def falar(texto: str) -> str:
    return Mensagem("falar", {"texto": texto}).para_json()


def normalizar_uid(uid: str) -> str:
    """UID de cartão em maiúsculas, sem separadores.

    O RC522 pode devolver '04 A1 B2 C3', '04:a1:b2:c3' ou '04A1B2C3' dependendo
    da biblioteca do firmware. Comparar UID sem normalizar é um bug silencioso:
    o cartão certo simplesmente não reconhece, e não há erro nenhum para ler.
    """
    return "".join(c for c in uid if c.isalnum()).upper()
