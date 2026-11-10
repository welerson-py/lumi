"""Cartões RFID → perfis. O cartão é um atalho, não uma credencial.

Cada cartão aponta para um perfil, e um perfil diz três coisas: que ações rodar
no PC, que rosto o robô faz, e — quando o LLM entrar — que persona a IA assume.

SOBRE O ARQUIVO DE CONFIGURAÇÃO: os perfis vivem em perfis.toml, fora do
código, para você cadastrar um cartão novo sem editar Python. O UID é
normalizado na leitura, porque o RC522 devolve o mesmo cartão em formatos
diferentes dependendo da biblioteca do firmware, e comparar sem normalizar
produz o pior tipo de bug: o cartão certo não funciona e não há erro nenhum
para ler.
"""

from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from protocolo import normalizar_uid

log = logging.getLogger("perfis")

ARQUIVO = Path(__file__).with_name("perfis.toml")


@dataclass
class Perfil:
    id: str
    nome: str
    acoes: list[str] = field(default_factory=list)
    rosto: str = "FELIZ"
    fala: str = ""
    persona: str = ""          # usado pelo LLM na etapa seguinte


class Perfis:
    def __init__(self, caminho: Path = ARQUIVO):
        self.caminho = caminho
        self.por_uid: dict[str, Perfil] = {}
        self.desconhecidos: list[str] = []
        self.carregar()

    def carregar(self) -> None:
        if not self.caminho.exists():
            log.warning("%s não existe; nenhum cartão cadastrado", self.caminho.name)
            self.por_uid = {}
            return

        with open(self.caminho, "rb") as f:
            dados = tomllib.load(f)

        novos: dict[str, Perfil] = {}
        for pid, bloco in (dados.get("perfil") or {}).items():
            perfil = Perfil(
                id=pid,
                nome=bloco.get("nome", pid),
                acoes=list(bloco.get("acoes", [])),
                rosto=bloco.get("rosto", "FELIZ"),
                fala=bloco.get("fala", ""),
                persona=bloco.get("persona", ""),
            )
            for uid in bloco.get("cartoes", []):
                chave = normalizar_uid(str(uid))
                if chave in novos:
                    log.warning("cartão %s aparece em dois perfis; vale o último", chave)
                novos[chave] = perfil

        self.por_uid = novos
        log.info("%d cartões carregados de %s", len(novos), self.caminho.name)

    def buscar(self, uid: str) -> Perfil | None:
        chave = normalizar_uid(uid)
        perfil = self.por_uid.get(chave)
        if perfil is None:
            # Registrar o desconhecido é o que torna o cadastro fácil: encoste o
            # cartão novo, leia o UID no log, cole no perfis.toml.
            if chave not in self.desconhecidos:
                self.desconhecidos.append(chave)
            log.info("cartão não cadastrado: %s  (cole este UID em perfis.toml)", chave)
        return perfil
