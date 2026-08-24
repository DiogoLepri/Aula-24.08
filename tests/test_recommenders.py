# -*- coding: utf-8 -*-
"""As prateleiras da home: cada uma escolhe o que promete escolher."""

import unittest

from src.data import consultas
from src.recommenders import PRATELEIRAS, aleatorio, populares, prateleiras, top10
from tests.base import ComBanco


class TestTop10(ComBanco):

    def test_ordena_pela_media(self):
        escolhidos = self.titulos(top10.selecionar(self.conexao))
        self.assertEqual(["Otimo e Visto", "Bom e Visto", "Campeao de Publico"], escolhidos[:3])

    def test_ignora_quem_nao_bate_o_minimo_de_avaliacoes(self):
        # 'Perfeito mas Obscuro' tem media 5,00 - a maior da base - com 3 notas.
        escolhidos = self.titulos(top10.selecionar(self.conexao))
        self.assertNotIn("Perfeito mas Obscuro", escolhidos)

    def test_o_minimo_e_o_da_listagem(self):
        self.assertEqual(consultas.MIN_AVALIACOES, 30)


class TestPopulares(ComBanco):

    def test_ordena_por_quantidade_e_nao_por_nota(self):
        escolhidos = self.titulos(populares.selecionar(self.conexao))
        self.assertEqual("Campeao de Publico", escolhidos[0])


class TestAleatorio(ComBanco):

    def test_so_traz_filme_com_alguma_avaliacao(self):
        for _ in range(10):
            escolhidos = self.titulos(aleatorio.selecionar(self.conexao))
            self.assertNotIn("Nunca Avaliado", escolhidos)

    def test_o_sorteio_muda(self):
        sorteios = {
            tuple(self.titulos(aleatorio.selecionar(self.conexao, limite=4)))
            for _ in range(20)
        }
        self.assertGreater(len(sorteios), 1)


class TestPrateleiras(ComBanco):

    def test_respeita_o_limite(self):
        for prateleira in prateleiras(self.conexao, limite=2):
            self.assertLessEqual(len(prateleira["filmes"]), 2)

    def test_todas_tem_a_mesma_forma(self):
        for prateleira in prateleiras(self.conexao):
            self.assertEqual(
                {"nome", "titulo", "linha", "link", "filmes"}, set(prateleira)
            )

    def test_a_home_monta_as_tres_do_quadro(self):
        nomes = [prateleira["nome"] for prateleira in prateleiras(self.conexao)]
        self.assertEqual(["top10", "populares", "aleatorio"], nomes)

    def test_cada_modulo_expoe_o_que_o_pacote_espera(self):
        for modulo in PRATELEIRAS:
            self.assertTrue(modulo.NOME and modulo.TITULO and modulo.LINK)
            self.assertTrue(modulo.linha())

    def test_o_cartao_traz_tudo_que_o_template_usa(self):
        cartao = prateleiras(self.conexao, limite=1)[0]["filmes"][0]
        self.assertEqual(
            {"id", "titulo", "ano", "poster", "qtd", "media", "categorias", "perfil"},
            set(cartao),
        )
        self.assertEqual(5, len(cartao["perfil"]))
        self.assertAlmostEqual(100.0, sum(faixa["fatia"] for faixa in cartao["perfil"]))


if __name__ == "__main__":
    unittest.main()
