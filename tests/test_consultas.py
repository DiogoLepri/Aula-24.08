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


class TestAprovacao(ComBanco):
    """A fatia de notas 4 e 5 - o numero verde do cartao."""

    def aprovacao_de(self, filme_id):
        linha = self.conexao.execute(
            "SELECT qtd, n1, n2, n3, n4, n5 FROM filme_estatistica WHERE filme_id = ?",
            (filme_id,),
        ).fetchone()
        return consultas.aprovacao(linha)

    def test_todo_mundo_gostou(self):
        # 'Otimo e Visto': 40 notas 5 e 10 notas 4, nada abaixo disso
        self.assertAlmostEqual(100.0, self.aprovacao_de(1))

    def test_ninguem_gostou(self):
        # 'Ruim': 35 notas 1
        self.assertAlmostEqual(0.0, self.aprovacao_de(5))

    def test_meio_a_meio(self):
        # 'Campeao de Publico': 70 de 100 notas sao 4 ou 5
        self.assertAlmostEqual(70.0, self.aprovacao_de(3))

    def test_filme_sem_nota_nao_tem_aprovacao(self):
        self.assertIsNone(self.aprovacao_de(7))


class TestDestaque(ComBanco):

    def test_sem_poster_no_banco_nao_ha_destaque(self):
        self.assertIsNone(consultas.destaque(self.conexao))

    def test_e_o_mais_avaliado_entre_os_que_tem_poster(self):
        # so 'Bom e Visto' e 'Campeao de Publico' ganham poster; o segundo tem
        # o dobro de avaliacoes
        self.conexao.execute("UPDATE filme SET poster = '/b.jpg' WHERE id = 2")
        self.conexao.execute("UPDATE filme SET poster = '/c.jpg' WHERE id = 3")
        self.assertEqual("Campeao de Publico", consultas.destaque(self.conexao)["titulo"])


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
