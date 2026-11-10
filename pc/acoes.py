"""Ações que o hub pode executar no computador e na casa.

A REGRA CENTRAL DESTE ARQUIVO, e o motivo de ele existir separado:

    o robô manda um NOME de ação, nunca um comando.

Nada que chega pela rede é interpretado como instrução para o sistema
operacional. O ESP32 envia "foco"; o Python procura "foco" num dicionário
escrito aqui, à mão, e executa a função correspondente. Se o nome não estiver
no dicionário, nada acontece.

Isso parece rigor excessivo num projeto de mesa, até lembrar o que este sistema
vai ser: um ouvido permanentemente ligado, conectado à rede local, com poder de
abrir programas e acionar tomadas. Um cartão RFID comum tem UID clonável com um
celular, e qualquer aparelho na mesma rede pode abrir uma conexão e mandar uma
mensagem inventada. Quando o LLM entrar na etapa seguinte, ele também vai
escolher apenas nomes desta lista — um modelo convencido a dizer "apague a
pasta X" não encontra caminho de código para isso virar execução, porque esse
caminho não existe.

O custo de manter a regra é uma função a mais por ação nova. O custo de
abandoná-la aparece uma vez só, e é caro.
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
import webbrowser
from dataclasses import dataclass
from typing import Callable

log = logging.getLogger("acoes")

SISTEMA = platform.system()      # 'Windows', 'Linux', 'Darwin'


@dataclass(frozen=True)
class Acao:
    nome: str
    descricao: str
    executar: Callable[[], bool]


_REGISTRO: dict[str, Acao] = {}


def registrar(nome: str, descricao: str):
    """Decorador que coloca uma função na lista de ações permitidas."""
    def envolver(fn: Callable[[], bool]) -> Callable[[], bool]:
        if nome in _REGISTRO:
            raise ValueError(f"ação duplicada: {nome}")
        _REGISTRO[nome] = Acao(nome, descricao, fn)
        return fn
    return envolver


def disponiveis() -> list[Acao]:
    return sorted(_REGISTRO.values(), key=lambda a: a.nome)


def executar(nome: str) -> bool:
    """Executa uma ação pelo nome. Devolve False se não existir ou falhar.

    Nunca levanta exceção para cima: uma ação que quebra não pode derrubar o
    servidor e deixar o robô mudo.
    """
    acao = _REGISTRO.get(nome)
    if acao is None:
        log.warning("ação desconhecida ignorada: %r", nome)
        return False
    try:
        ok = acao.executar()
        log.info("ação %s -> %s", nome, "ok" if ok else "falhou")
        return bool(ok)
    except Exception as e:                      # noqa: BLE001 - contenção proposital
        log.error("ação %s levantou %s: %s", nome, e.__class__.__name__, e)
        return False


# ------------------------------------------------------------------
# utilidades de sistema
# ------------------------------------------------------------------
def _abrir(caminho_ou_url: str) -> bool:
    """Abre um arquivo, pasta ou URL com o programa padrão do sistema."""
    try:
        if caminho_ou_url.startswith(("http://", "https://")):
            return webbrowser.open(caminho_ou_url)
        if not os.path.exists(caminho_ou_url):
            # Sem esta linha a ação diz "ok" e nada abre: o comando do sistema
            # sai em outro processo e o erro dele nunca volta para cá.
            log.warning("caminho não existe: %s", caminho_ou_url)
            return False
        if SISTEMA == "Windows":
            os.startfile(caminho_ou_url)        # type: ignore[attr-defined]
        elif SISTEMA == "Darwin":
            subprocess.Popen(["open", caminho_ou_url])
        else:
            subprocess.Popen(["xdg-open", caminho_ou_url])
        return True
    except Exception as e:                      # noqa: BLE001
        log.error("não consegui abrir %s: %s", caminho_ou_url, e)
        return False


def _rodar(programa: str, *args: str) -> bool:
    """Roda um executável já conhecido. `programa` vem sempre do código, nunca
    da rede — é por isso que shell=False e a lista de argumentos é explícita."""
    caminho = shutil.which(programa)
    if caminho is None:
        log.warning("programa não encontrado no PATH: %s", programa)
        return False
    try:
        subprocess.Popen([caminho, *args], shell=False)
        return True
    except Exception as e:                      # noqa: BLE001
        log.error("falha ao rodar %s: %s", programa, e)
        return False


# ------------------------------------------------------------------
# ações — acrescente as suas aqui
# ------------------------------------------------------------------
@registrar("foco", "Modo foco: abre o editor e silencia distrações")
def acao_foco() -> bool:
    ok = _rodar("code")                          # VS Code, se estiver no PATH
    return ok


@registrar("estudos", "Abre a pasta de estudos e o material da faculdade")
def acao_estudos() -> bool:
    pasta = os.path.expanduser("~/Documents")
    return _abrir(pasta)


@registrar("receitas", "Abre o caderno de receitas")
def acao_receitas() -> bool:
    return _abrir("https://www.google.com/search?q=receitas")


@registrar("navegador", "Abre o navegador padrão")
def acao_navegador() -> bool:
    return _abrir("https://duckduckgo.com")


@registrar("nada", "Não faz nada. Útil para um perfil que só muda a persona da IA")
def acao_nada() -> bool:
    return True


# ------------------------------------------------------------------
# casa inteligente — deliberadamente separado e ainda vazio
# ------------------------------------------------------------------
# Este bloco é o mais provável de mudar, e por isso está isolado.
#
# A maioria das tomadas e lâmpadas Wi-Fi baratas (Tuya, Smart Life, e as marcas
# de supermercado que usam o mesmo chip) só aceita comando pela nuvem do
# fabricante: o teu cartão RFID acionaria um servidor na China para acender uma
# lâmpada a dois metros de ti, e deixaria de funcionar se a internet cair ou se
# o fabricante encerrar o serviço.
#
# Alternativas com controle local de verdade:
#   - Shelly: API HTTP local, documentada, sem nuvem obrigatória
#   - qualquer dispositivo com Tasmota instalado
#   - Home Assistant como camada única na frente de tudo
#
# Quando você escolher, implemente aqui como função registrada, do mesmo jeito
# que as de cima. A assinatura não muda nada no resto do sistema.

@registrar("luz_foco", "Luzes em modo foco (ainda não implementado)")
def acao_luz_foco() -> bool:
    log.info("luz_foco: sem dispositivo configurado ainda")
    return False
