# -*- coding: utf-8 -*-
"""Mais avaliados: os filmes que mais gente notou.

Nada a ver com nota - e so volume. Em 1997 isso era, na pratica, o que estava
passando: o que apareceu mais vezes na tela de quem estava avaliando.
"""

from src.data import consultas

NOME = "populares"
TITULO = "Os mais avaliados"
LINK = "/filmes?ordem=avaliados"


def linha():
    return "Os dez que mais gente viu e notou - volume, nao nota."


def selecionar(conexao, limite=10):
    return consultas.cartoes(
        conexao,
        ordem="e.qtd DESC, f.titulo_busca",
        limite=limite,
    )
