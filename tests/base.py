# -*- coding: utf-8 -*-
"""Um banco de brinquedo, criado com o esquema de verdade.

Sete filmes com notas escolhidas na mao, para dar para conferir de cabeca o
que cada prateleira deveria devolver.
"""

import sqlite3
import unittest

from src.data import banco as bd

CATEGORIAS = [(0, "Action"), (1, "Comedy"), (2, "Drama")]

# (id, titulo_busca, ano, categorias, [(nota, quantas vezes), ...])
FILMES = [
    (1, "Otimo e Visto",      1994, [2],    [(5, 40), (4, 10)]),          # media 4,80 / 50 notas
    (2, "Bom e Visto",        1995, [0, 2], [(5, 20), (4, 20), (3, 10)]), # media 4,20 / 50 notas
    (3, "Campeao de Publico", 1977, [0],    [(5, 30), (4, 40), (3, 30)]), # media 4,00 / 100 notas
    (4, "Mediano",            1996, [1],    [(3, 30), (2, 10)]),          # media 2,75 / 40 notas
    (5, "Ruim",               1993, [1],    [(1, 35)]),                   # media 1,00 / 35 notas
    (6, "Perfeito mas Obscuro", 1990, [2],  [(5, 3)]),                    # media 5,00 / 3 notas
    (7, "Nunca Avaliado",     1980, [1],    []),                          # sem nota nenhuma
]


def banco_de_teste():
    """Conexao em memoria com o esquema de verdade e os filmes acima."""
    conexao = sqlite3.connect(":memory:")
    conexao.row_factory = sqlite3.Row
    bd.criar_esquema(conexao)

    conexao.executemany("INSERT INTO categoria (id, nome) VALUES (?, ?)", CATEGORIAS)

    usuario = 0
    for filme_id, titulo, ano, categorias, notas in FILMES:
        conexao.execute(
            "INSERT INTO filme (id, titulo, titulo_busca, ano) VALUES (?, ?, ?, ?)",
            (filme_id, titulo, titulo, ano),
        )
        for categoria_id in categorias:
            conexao.execute(
                "INSERT INTO filme_categoria (filme_id, categoria_id) VALUES (?, ?)",
                (filme_id, categoria_id),
            )
        for nota, quantas in notas:
            for _ in range(quantas):
                usuario += 1
                conexao.execute(
                    "INSERT INTO usuario (id, idade, sexo) VALUES (?, 30, 'M')", (usuario,)
                )
                conexao.execute(
                    "INSERT INTO avaliacao (usuario_id, filme_id, nota, avaliado_em)"
                    " VALUES (?, ?, ?, 0)",
                    (usuario, filme_id, nota),
                )

    conexao.execute(
        """
        INSERT INTO filme_estatistica (filme_id, qtd, media, n1, n2, n3, n4, n5)
        SELECT f.id, COUNT(a.nota), AVG(a.nota),
               COALESCE(SUM(a.nota = 1), 0), COALESCE(SUM(a.nota = 2), 0),
               COALESCE(SUM(a.nota = 3), 0), COALESCE(SUM(a.nota = 4), 0),
               COALESCE(SUM(a.nota = 5), 0)
        FROM filme f LEFT JOIN avaliacao a ON a.filme_id = f.id
        GROUP BY f.id
        """
    )
    conexao.commit()
    return conexao


class ComBanco(unittest.TestCase):
    """Base para os testes que precisam do banco de brinquedo."""

    def setUp(self):
        self.conexao = banco_de_teste()

    def tearDown(self):
        self.conexao.close()

    def titulos(self, cartoes):
        return [cartao["titulo"] for cartao in cartoes]
