# -*- coding: utf-8 -*-
"""O esquema: as tabelas do quadro existem e as regras seguram os erros."""

import sqlite3
import unittest

from tests.base import ComBanco

TABELAS = {
    "filme", "categoria", "filme_categoria", "pessoa", "filme_pessoa",
    "usuario", "avaliacao", "filme_estatistica",
}


class TestEsquema(ComBanco):

    def test_todas_as_tabelas_do_quadro_existem(self):
        criadas = {
            linha["name"]
            for linha in self.conexao.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        self.assertEqual(TABELAS, criadas & TABELAS)

    def test_nota_fora_de_1_a_5_e_recusada(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conexao.execute(
                "INSERT INTO avaliacao (usuario_id, filme_id, nota, avaliado_em)"
                " VALUES (1, 1, 6, 0)"
            )

    def test_mesma_pessoa_nao_avalia_o_mesmo_filme_duas_vezes(self):
        self.conexao.execute(
            "INSERT INTO usuario (id, idade, sexo) VALUES (9001, 20, 'F')"
        )
        self.conexao.execute(
            "INSERT INTO avaliacao (usuario_id, filme_id, nota, avaliado_em)"
            " VALUES (9001, 1, 4, 0)"
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.conexao.execute(
                "INSERT INTO avaliacao (usuario_id, filme_id, nota, avaliado_em)"
                " VALUES (9001, 1, 5, 0)"
            )

    def test_papel_so_aceita_ator_ou_diretor(self):
        self.conexao.execute("INSERT INTO pessoa (id, nome) VALUES (1, 'Fulana')")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conexao.execute(
                "INSERT INTO filme_pessoa (filme_id, pessoa_id, papel) VALUES (1, 1, 'figurante')"
            )

    def test_mesma_pessoa_pode_dirigir_e_atuar_no_mesmo_filme(self):
        self.conexao.execute("INSERT INTO pessoa (id, nome) VALUES (1, 'Fulana')")
        self.conexao.execute(
            "INSERT INTO filme_pessoa (filme_id, pessoa_id, papel) VALUES (1, 1, 'diretor')"
        )
        self.conexao.execute(
            "INSERT INTO filme_pessoa (filme_id, pessoa_id, papel, ordem) VALUES (1, 1, 'ator', 0)"
        )
        papeis = [
            linha["papel"]
            for linha in self.conexao.execute(
                "SELECT papel FROM filme_pessoa WHERE filme_id = 1 ORDER BY papel"
            )
        ]
        self.assertEqual(["ator", "diretor"], papeis)

    def test_um_filme_pode_estar_em_varios_generos(self):
        generos = self.conexao.execute(
            "SELECT COUNT(*) FROM filme_categoria WHERE filme_id = 2"
        ).fetchone()[0]
        self.assertEqual(2, generos)

    def test_estatistica_bate_com_as_avaliacoes(self):
        linha = self.conexao.execute(
            "SELECT qtd, media, n4, n5 FROM filme_estatistica WHERE filme_id = 1"
        ).fetchone()
        self.assertEqual(50, linha["qtd"])
        self.assertAlmostEqual(4.8, linha["media"], places=2)
        self.assertEqual(10, linha["n4"])
        self.assertEqual(40, linha["n5"])

    def test_filme_sem_nota_entra_na_estatistica_zerado(self):
        linha = self.conexao.execute(
            "SELECT qtd, media FROM filme_estatistica WHERE filme_id = 7"
        ).fetchone()
        self.assertEqual(0, linha["qtd"])
        self.assertIsNone(linha["media"])


if __name__ == "__main__":
    unittest.main()
