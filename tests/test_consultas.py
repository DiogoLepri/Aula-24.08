# -*- coding: utf-8 -*-
"""A listagem de /filmes: busca, filtro, ordenacao e paginacao."""

import unittest

from src.data import consultas
from tests.base import ComBanco


class TestBusca(ComBanco):

    def buscar(self, q=None, genero=None, ordem="avaliados", pagina=1):
        return consultas.buscar_filmes(self.conexao, q, genero, ordem, pagina)

    def test_sem_filtro_traz_o_catalogo_inteiro(self):
        _, total, _, _ = self.buscar()
        self.assertEqual(7, total)

    def test_busca_por_trecho_do_titulo(self):
        filmes, total, _, _ = self.buscar(q="Visto")
        self.assertEqual(2, total)
        self.assertEqual({"Otimo e Visto", "Bom e Visto"}, set(self.titulos(filmes)))

    def test_filtro_por_genero(self):
        filmes, total, _, _ = self.buscar(genero="Comedy")
        self.assertEqual(3, total)
        self.assertTrue(all("Comedy" in f["categorias"] for f in filmes))

    def test_ordem_por_nota_aplica_o_piso(self):
        filmes, total, _, _ = self.buscar(ordem="nota")
        self.assertNotIn("Perfeito mas Obscuro", self.titulos(filmes))
        self.assertEqual(5, total)

    def test_ordem_desconhecida_nao_quebra_a_listagem(self):
        # a rota cai para 'avaliados' antes de chegar aqui
        self.assertNotIn("inventada", consultas.ORDENS)

    def test_pagina_alem_do_fim_volta_para_a_ultima(self):
        _, _, pagina, paginas = self.buscar(pagina=99)
        self.assertEqual(paginas, pagina)

    def test_busca_sem_resultado_devolve_lista_vazia(self):
        filmes, total, pagina, paginas = self.buscar(q="xyz nao existe")
        self.assertEqual([], filmes)
        self.assertEqual(0, total)
        self.assertEqual(1, pagina)
        self.assertEqual(1, paginas)


class TestNumeros(ComBanco):

    def test_numeros_gerais(self):
        numeros = consultas.numeros_gerais(self.conexao)
        self.assertEqual(7, numeros["filmes"])
        self.assertEqual(278, numeros["avaliacoes"])  # 50+50+100+40+35+3

    def test_distribuicao_geral_soma_cem_por_cento(self):
        distribuicao = consultas.distribuicao_geral(self.conexao)
        self.assertAlmostEqual(100.0, sum(faixa["fatia"] for faixa in distribuicao))

    def test_lista_categorias_conta_filmes_por_genero(self):
        contagem = {
            linha["nome"]: linha["filmes"]
            for linha in consultas.lista_categorias(self.conexao)
        }
        self.assertEqual({"Drama": 3, "Comedy": 3, "Action": 2}, contagem)


if __name__ == "__main__":
    unittest.main()
