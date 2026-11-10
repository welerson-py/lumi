"""Hub robótico de mesa — programa principal do PC.

Este arquivo é a cola: recebe eventos do robô, decide o que fazer, manda de
volta o rosto e a fala. A decisão está aqui e em perfis.toml; a execução está
em acoes.py; o transporte está em servidor.py. Cada peça pode ser trocada sem
mexer nas outras.

    python main.py                 # espera o robô conectar
    python simular.py rfid 04A1B2C3    # (noutro terminal) finge ser o robô

Etapa atual: RFID → perfil → ações no PC → rosto e fala de volta.
Próximas: voz (INMP441/MAX98357) e o LLM local escolhendo ações da lista.
"""

from __future__ import annotations

import asyncio
import logging
import socket

import acoes
from perfis import Perfis
from protocolo import Mensagem, VERSAO
from servidor import Ligacao, Servidor

log = logging.getLogger("hub")

# Carregado em main(), depois do logging: se os perfis fossem lidos aqui no
# topo, um erro no perfis.toml apareceria como traceback cru antes de existir
# log, e a linha "N cartões carregados" se perderia.
perfis: Perfis | None = None
perfil_atual = None


async def ao_receber(msg: Mensagem, robo: Ligacao) -> None:
    global perfil_atual, perfis

    if msg.tipo == "ola":
        nome = msg.dados.get("nome", "robô")
        versao = msg.dados.get("versao")
        robo.nome = nome
        if versao != VERSAO:
            # Não é fatal, mas é a explicação de 90% dos "conecta e não reage".
            log.warning("robô %s fala a versão %s; o PC fala a %s",
                        nome, versao, VERSAO)
        log.info("olá, %s", nome)
        await robo.estado("OCIOSO")
        return

    if msg.tipo == "rfid":
        if perfis is None:                 # importado sem passar por main()
            perfis = Perfis()
        uid = str(msg.dados.get("uid", ""))
        perfil = perfis.buscar(uid)

        if perfil is None:
            await robo.estado("ERRO")
            await robo.falar("Cartão não cadastrado.")
            await asyncio.sleep(1.5)
            await robo.estado("OCIOSO")
            return

        perfil_atual = perfil
        log.info("perfil ativado: %s", perfil.nome)

        # o rosto muda antes das ações: abrir um programa demora, e o robô
        # parado durante a espera parece travado
        await robo.estado(perfil.rosto)
        await robo.gesto("atencao")

        resultados = [acoes.executar(nome) for nome in perfil.acoes]
        if perfil.fala:
            await robo.falar(perfil.fala)

        if resultados and not any(resultados):
            # nenhuma ação funcionou: melhor dizer do que fingir que deu certo
            log.warning("nenhuma ação do perfil %s funcionou", perfil.id)
            await robo.estado("ERRO")
            await asyncio.sleep(1.5)
            await robo.estado(perfil.rosto)   # o perfil segue ativo mesmo assim
        return

    if msg.tipo == "botao":
        log.info("botão %s", msg.dados.get("qual"))
        await robo.estado("OUVINDO")
        return

    if msg.tipo == "erro":
        log.error("robô relatou: %s", msg.dados.get("mensagem"))
        await robo.estado("ERRO")
        return

    log.debug("mensagem ignorada: %s", msg.tipo)


def ip_da_rede() -> str:
    """Endereço deste PC na rede local — é o que vai no firmware do ESP32.

    Não abre conexão nenhuma: pergunta ao sistema qual interface ele usaria
    para sair, e lê o endereço dela. Funciona com Wi-Fi e cabo, e não depende
    de haver internet.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def main() -> None:
    global perfis

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(name)-9s %(message)s",
        datefmt="%H:%M:%S",
    )
    print("ações registradas:")
    for a in acoes.disponiveis():
        print(f"  {a.nome:<12} {a.descricao}")
    print()

    perfis = Perfis()
    print(f"no firmware do ESP32, use:  ws://{ip_da_rede()}:8765\n")

    servidor = Servidor(ao_receber)
    try:
        asyncio.run(servidor.rodar())
    except KeyboardInterrupt:
        print("\nencerrado")


if __name__ == "__main__":
    main()
