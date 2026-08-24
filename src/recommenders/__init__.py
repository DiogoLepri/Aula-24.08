# -*- coding: utf-8 -*-
"""As prateleiras da home.

Cada modulo daqui responde uma pergunta - o que e bom, o que todo mundo viu, o
que voce ainda nao pensou em ver - e devolve os dez filmes que respondem.
Todos tem a mesma forma: NOME, TITULO, LINK, linha() e selecionar(conexao).

A home so monta o que sair de prateleiras(); para mudar a ordem, tirar ou
acrescentar uma prateleira, mexe-se so na tupla PRATELEIRAS.
"""

from src.recommenders import aleatorio, populares, top10

LIMITE = 10

PRATELEIRAS = (top10, populares, aleatorio)


def prateleiras(conexao, limite=LIMITE):
    """Todas as prateleiras prontas para o template."""
    return [
        {
            "nome": modulo.NOME,
            "titulo": modulo.TITULO,
            "linha": modulo.linha(),
            "link": modulo.LINK,
            "filmes": modulo.selecionar(conexao, limite),
        }
        for modulo in PRATELEIRAS
    ]
