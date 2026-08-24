# -*- coding: utf-8 -*-
"""Aleatorio: dez filmes sorteados, para sair do topo da lista.

O sorteio e do SQLite (ORDER BY RANDOM()), entao muda a cada visita. So entram
filmes com alguma avaliacao - senao a prateleira enche de titulo que ninguem
viu, sem barra de notas nenhuma.
"""

from src.data import consultas

NOME = "aleatorio"
TITULO = "Aleatorio"
LINK = "/filmes?ordem=titulo"


def linha():
    return "Dez filmes sorteados da base. Recarregue a pagina para outros dez."


def selecionar(conexao, limite=10):
    return consultas.cartoes(
        conexao,
        onde="WHERE e.qtd > 0",
        ordem="RANDOM()",
        limite=limite,
    )
