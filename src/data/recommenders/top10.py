# -*- coding: utf-8 -*-
"""Top 10: as melhores medias do catalogo.

Com piso de avaliacoes. Sem ele, o topo seria uma fila de filmes que tres
pessoas viram e adoraram - media 5,00 em 3 notas nao diz nada.
"""

from src.data import consultas

NOME = "top10"
TITULO = "Top 10"
LINK = "/filmes?ordem=nota"


def linha():
    return (
        f"As dez melhores médias entre os filmes com pelo menos "
        f"{consultas.MIN_AVALIACOES} avaliações."
    )


def selecionar(conexao, limite=10):
    return consultas.cartoes(
        conexao,
        onde="WHERE e.qtd >= ?",
        parametros=(consultas.MIN_AVALIACOES,),
        ordem="e.media DESC, e.qtd DESC",
        limite=limite,
    )
