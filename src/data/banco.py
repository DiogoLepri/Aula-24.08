# -*- coding: utf-8 -*-
"""Acesso ao SQLite: onde fica o arquivo, como abrir e como criar o esquema.

Um lugar so para isso, para que api, carga e recommenders nao repitam o
caminho do banco nem a configuracao da conexao.
"""

import os
import sqlite3

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))

ESQUEMA_SQL = os.path.join(AQUI, "esquema.sql")
BANCO_PADRAO = os.environ.get("MOVIELENS_DB", os.path.join(RAIZ, "movielens.db"))


def caminho(banco=None):
    """O arquivo do banco: o informado, ou MOVIELENS_DB, ou movielens.db na raiz."""
    return banco or BANCO_PADRAO


def conectar(banco=None):
    """Conexao com linhas acessiveis por nome de coluna."""
    conexao = sqlite3.connect(caminho(banco))
    conexao.row_factory = sqlite3.Row
    return conexao


def conexao_web():
    """Dependencia do FastAPI: uma conexao por requisicao, fechada no fim."""
    conexao = conectar()
    try:
        yield conexao
    finally:
        conexao.close()


def criar_esquema(conexao):
    """Roda esquema.sql. Apaga e recria todas as tabelas."""
    with open(ESQUEMA_SQL, encoding="utf-8") as arquivo:
        conexao.executescript(arquivo.read())
