# -*- coding: utf-8 -*-
"""Carrega o MovieLens 100k num banco SQLite.

    python carga.py --dados ~/Downloads/ml-100k --banco movielens.db

Le u.item, u.genre, u.data e u.user e cria o banco do zero (apaga e recria as
tabelas a cada execucao). Nao depende de pandas - so da biblioteca padrao.

Sobre os formatos: apesar do que diz o README do dataset, so u.data e separado
por tabulacao. u.item, u.user e u.genre usam '|', e todos vem em latin-1.

As tabelas pessoa e filme_pessoa nascem vazias: ator e diretor nao existem em
lugar nenhum do ml-100k. Quem preenche e o scraper.py.
"""

import argparse
import csv
import os
import re
import sqlite3
import sys

ESQUEMA = """
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS filme_estatistica;
DROP TABLE IF EXISTS avaliacao;
DROP TABLE IF EXISTS filme_pessoa;
DROP TABLE IF EXISTS filme_categoria;
DROP TABLE IF EXISTS pessoa;
DROP TABLE IF EXISTS categoria;
DROP TABLE IF EXISTS usuario;
DROP TABLE IF EXISTS filme;

CREATE TABLE filme (
    id              INTEGER PRIMARY KEY,
    titulo          TEXT NOT NULL,
    titulo_busca    TEXT NOT NULL,
    titulo_alt      TEXT,
    ano             INTEGER,
    data_lancamento TEXT,
    imdb_url        TEXT,
    poster          TEXT
);

CREATE TABLE categoria (
    id   INTEGER PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE
);

CREATE TABLE filme_categoria (
    filme_id     INTEGER NOT NULL REFERENCES filme(id),
    categoria_id INTEGER NOT NULL REFERENCES categoria(id),
    PRIMARY KEY (filme_id, categoria_id)
);

CREATE TABLE pessoa (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    nome    TEXT NOT NULL UNIQUE,
    tmdb_id INTEGER,
    foto    TEXT
);

CREATE TABLE filme_pessoa (
    filme_id  INTEGER NOT NULL REFERENCES filme(id),
    pessoa_id INTEGER NOT NULL REFERENCES pessoa(id),
    papel     TEXT NOT NULL CHECK (papel IN ('ator', 'diretor')),
    ordem     INTEGER,
    PRIMARY KEY (filme_id, pessoa_id, papel)
);

CREATE TABLE usuario (
    id       INTEGER PRIMARY KEY,
    idade    INTEGER,
    sexo     TEXT CHECK (sexo IN ('M', 'F')),
    ocupacao TEXT,
    cep      TEXT
);

CREATE TABLE avaliacao (
    usuario_id  INTEGER NOT NULL REFERENCES usuario(id),
    filme_id    INTEGER NOT NULL REFERENCES filme(id),
    nota        INTEGER NOT NULL CHECK (nota BETWEEN 1 AND 5),
    avaliado_em INTEGER NOT NULL,
    PRIMARY KEY (usuario_id, filme_id)
);

CREATE TABLE filme_estatistica (
    filme_id INTEGER PRIMARY KEY REFERENCES filme(id),
    qtd      INTEGER NOT NULL DEFAULT 0,
    media    REAL,
    n1       INTEGER NOT NULL DEFAULT 0,
    n2       INTEGER NOT NULL DEFAULT 0,
    n3       INTEGER NOT NULL DEFAULT 0,
    n4       INTEGER NOT NULL DEFAULT 0,
    n5       INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_avaliacao_filme ON avaliacao(filme_id);
CREATE INDEX idx_filme_categoria_categoria ON filme_categoria(categoria_id);
CREATE INDEX idx_filme_pessoa_pessoa ON filme_pessoa(pessoa_id);
CREATE INDEX idx_filme_ano ON filme(ano);
CREATE INDEX idx_estatistica_qtd ON filme_estatistica(qtd);
CREATE INDEX idx_estatistica_media ON filme_estatistica(media);
"""

ARTIGOS = {
    "the", "a", "an",
    "la", "le", "les", "l'", "un", "une",
    "il", "lo", "gli", "i",
    "el", "los", "las",
    "der", "die", "das", "ein", "eine",
    "de", "het", "een",
    "os", "as", "uma",
}

MESES = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
    "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}


def normalizar_titulo(titulo_bruto):
    """Devolve (titulo_busca, titulo_alt, ano).

    O MovieLens escreve o titulo em tres padroes que atrapalham qualquer busca
    externa: o ano no fim entre parenteses, o artigo jogado para depois da
    virgula e um titulo alternativo em parenteses no meio.
    """
    texto = titulo_bruto.strip()

    ano = None
    casamento = re.search(r"\((\d{4})\)\s*$", texto)
    if casamento:
        ano = int(casamento.group(1))
        texto = texto[: casamento.start()].strip()

    alternativo = None
    casamento = re.search(r"\(([^()]+)\)\s*$", texto)
    if casamento:
        alternativo = casamento.group(1).strip()
        texto = texto[: casamento.start()].strip()

    partes = texto.rsplit(", ", 1)
    if len(partes) == 2 and partes[1].lower().rstrip(".") in ARTIGOS:
        artigo = partes[1]
        separador = "" if artigo.endswith("'") else " "
        texto = f"{artigo}{separador}{partes[0]}"

    if alternativo:
        partes = alternativo.rsplit(", ", 1)
        if len(partes) == 2 and partes[1].lower().rstrip(".") in ARTIGOS:
            artigo = partes[1]
            separador = "" if artigo.endswith("'") else " "
            alternativo = f"{artigo}{separador}{partes[0]}"

    return texto.strip(), alternativo, ano


def data_iso(bruto):
    """'01-Jan-1995' -> '1995-01-01'. Devolve None para vazio ou formato estranho."""
    if not bruto:
        return None
    partes = bruto.strip().split("-")
    if len(partes) != 3:
        return None
    dia, mes, ano = partes
    mes = MESES.get(mes.lower())
    if not mes or not ano.isdigit():
        return None
    return f"{ano}-{mes}-{int(dia):02d}"


def ler_linhas(caminho, separador):
    with open(caminho, encoding="latin-1", newline="") as arquivo:
        for linha in csv.reader(arquivo, delimiter=separador):
            if linha:
                yield linha


def achar_pasta(informada):
    candidatas = []
    if informada:
        candidatas.append(os.path.expanduser(informada))
    aqui = os.path.dirname(os.path.abspath(__file__))
    candidatas += [
        aqui,
        os.path.join(aqui, "ml-100k"),
        os.path.join(os.path.expanduser("~"), "Downloads", "ml-100k"),
    ]
    for pasta in candidatas:
        if all(os.path.exists(os.path.join(pasta, f)) for f in ("u.data", "u.item", "u.user")):
            return pasta
    print(
        "Nao encontrei os arquivos do ml-100k (u.data, u.item, u.user).\n"
        "Procurei em:\n  " + "\n  ".join(candidatas) + "\n\n"
        "Passe a pasta com --dados:\n"
        "  python carga.py --dados ~/Downloads/ml-100k",
        file=sys.stderr,
    )
    sys.exit(1)


def carregar(pasta, caminho_banco):
    if os.path.exists(caminho_banco):
        os.remove(caminho_banco)

    conexao = sqlite3.connect(caminho_banco)
    conexao.executescript(ESQUEMA)

    categorias = []
    for linha in ler_linhas(os.path.join(pasta, "u.genre"), "|"):
        if len(linha) >= 2 and linha[0].strip():
            categorias.append((int(linha[1]), linha[0].strip()))
    categorias.sort()
    conexao.executemany("INSERT INTO categoria (id, nome) VALUES (?, ?)", categorias)
    nomes_categorias = [nome for _, nome in categorias]

    filmes, vinculos = [], []
    for linha in ler_linhas(os.path.join(pasta, "u.item"), "|"):
        filme_id = int(linha[0])
        titulo = linha[1].strip()
        busca, alternativo, ano = normalizar_titulo(titulo)
        lancamento = data_iso(linha[2] if len(linha) > 2 else "")
        if ano is None and lancamento:
            ano = int(lancamento[:4])
        url = (linha[4].strip() or None) if len(linha) > 4 else None

        filmes.append((filme_id, titulo, busca, alternativo, ano, lancamento, url))
        for posicao, marcado in enumerate(linha[5:5 + len(nomes_categorias)]):
            if marcado.strip() == "1":
                vinculos.append((filme_id, posicao))

    conexao.executemany(
        "INSERT INTO filme (id, titulo, titulo_busca, titulo_alt, ano, data_lancamento,"
        " imdb_url) VALUES (?, ?, ?, ?, ?, ?, ?)",
        filmes,
    )
    conexao.executemany(
        "INSERT INTO filme_categoria (filme_id, categoria_id) VALUES (?, ?)", vinculos
    )

    usuarios = [
        (int(l[0]), int(l[1]), l[2].strip(), l[3].strip(), l[4].strip())
        for l in ler_linhas(os.path.join(pasta, "u.user"), "|")
    ]
    conexao.executemany(
        "INSERT INTO usuario (id, idade, sexo, ocupacao, cep) VALUES (?, ?, ?, ?, ?)",
        usuarios,
    )

    avaliacoes = [
        (int(l[0]), int(l[1]), int(l[2]), int(l[3]))
        for l in ler_linhas(os.path.join(pasta, "u.data"), "\t")
    ]
    conexao.executemany(
        "INSERT OR IGNORE INTO avaliacao (usuario_id, filme_id, nota, avaliado_em)"
        " VALUES (?, ?, ?, ?)",
        avaliacoes,
    )

    conexao.execute(
        """
        INSERT INTO filme_estatistica (filme_id, qtd, media, n1, n2, n3, n4, n5)
        SELECT f.id,
               COUNT(a.nota),
               AVG(a.nota),
               COALESCE(SUM(a.nota = 1), 0),
               COALESCE(SUM(a.nota = 2), 0),
               COALESCE(SUM(a.nota = 3), 0),
               COALESCE(SUM(a.nota = 4), 0),
               COALESCE(SUM(a.nota = 5), 0)
        FROM filme f
        LEFT JOIN avaliacao a ON a.filme_id = f.id
        GROUP BY f.id
        """
    )

    conexao.commit()

    inseridas = conexao.execute("SELECT COUNT(*) FROM avaliacao").fetchone()[0]
    sem_nota = conexao.execute(
        "SELECT COUNT(*) FROM filme_estatistica WHERE qtd = 0"
    ).fetchone()[0]
    sem_ano = conexao.execute("SELECT COUNT(*) FROM filme WHERE ano IS NULL").fetchone()[0]
    titulos_repetidos = conexao.execute(
        "SELECT COUNT(*) FROM (SELECT titulo_busca FROM filme GROUP BY titulo_busca"
        " HAVING COUNT(*) > 1)"
    ).fetchone()[0]
    conexao.close()

    print(f"Banco criado em {caminho_banco}")
    print(f"  {len(filmes):>6} filmes, {len(vinculos)} vinculos com categoria")
    print(f"  {len(usuarios):>6} usuarios")
    print(f"  {inseridas:>6} avaliacoes ({len(avaliacoes) - inseridas} descartadas por duplicidade)")
    print(f"  {sem_nota:>6} filmes sem nenhuma nota")
    print(f"  {sem_ano:>6} filmes sem ano")
    print(f"  {titulos_repetidos:>6} titulos que aparecem em mais de um id")
    print("\n  pessoa e filme_pessoa estao vazias - rode o scraper.py para preenche-las.")


def main():
    parser = argparse.ArgumentParser(description="Carrega o ml-100k num banco SQLite.")
    parser.add_argument("--dados", help="pasta com u.data, u.item, u.user, u.genre")
    parser.add_argument("--banco", default="movielens.db", help="arquivo SQLite de saida")
    argumentos = parser.parse_args()
    carregar(achar_pasta(argumentos.dados), argumentos.banco)


if __name__ == "__main__":
    main()
