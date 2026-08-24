# -*- coding: utf-8 -*-
"""As consultas que a aplicacao faz no banco.

Tudo que le filme + estatistica passa por aqui, para a listagem, a home e as
prateleiras montarem o mesmo cartao, com os mesmos campos.
"""

import math

POR_PAGINA = 24

# Piso para qualquer ranking por nota. Sem ele o topo vira uma fila de filmes
# com tres notas 5.
MIN_AVALIACOES = 30

CAMPOS_CARTAO = """
    SELECT f.id, f.titulo, f.titulo_busca, f.ano, f.poster, e.qtd, e.media,
           e.n1, e.n2, e.n3, e.n4, e.n5
    FROM filme f
    JOIN filme_estatistica e ON e.filme_id = f.id
"""

ORDENS = {
    "avaliados": ("mais avaliados", "e.qtd DESC, f.titulo_busca"),
    "nota": ("melhor nota", "e.media DESC, e.qtd DESC"),
    "ano": ("mais recentes", "f.ano DESC, f.titulo_busca"),
    "titulo": ("titulo A-Z", "f.titulo_busca"),
}


def perfil(linha):
    """A distribuicao 1-5 do filme, em contagem e em porcentagem."""
    contagens = [linha["n1"], linha["n2"], linha["n3"], linha["n4"], linha["n5"]]
    total = sum(contagens) or 1
    return [
        {"nota": i + 1, "qtd": qtd, "fatia": qtd / total * 100}
        for i, qtd in enumerate(contagens)
    ]


def categorias_de(conexao, filme_ids):
    """Os generos de varios filmes de uma vez: {filme_id: [nome, ...]}."""
    if not filme_ids:
        return {}
    marcadores = ",".join("?" * len(filme_ids))
    linhas = conexao.execute(
        f"""
        SELECT fc.filme_id, c.nome
        FROM filme_categoria fc
        JOIN categoria c ON c.id = fc.categoria_id
        WHERE fc.filme_id IN ({marcadores})
        ORDER BY c.nome
        """,
        filme_ids,
    ).fetchall()
    agrupado = {}
    for linha in linhas:
        agrupado.setdefault(linha["filme_id"], []).append(linha["nome"])
    return agrupado


def montar_cartoes(conexao, linhas):
    """Transforma linhas do banco no dicionario que o template do cartao espera."""
    por_filme = categorias_de(conexao, [linha["id"] for linha in linhas])
    return [
        {
            "id": linha["id"],
            "titulo": linha["titulo_busca"],
            "ano": linha["ano"],
            "poster": linha["poster"],
            "qtd": linha["qtd"],
            "media": linha["media"],
            "categorias": por_filme.get(linha["id"], []),
            "perfil": perfil(linha),
        }
        for linha in linhas
    ]


def cartoes(conexao, onde="", parametros=(), ordem="e.qtd DESC", limite=10):
    """Uma selecao de filmes ja no formato de cartao. E a base das prateleiras."""
    linhas = conexao.execute(
        f"{CAMPOS_CARTAO} {onde} ORDER BY {ordem} LIMIT ?",
        list(parametros) + [limite],
    ).fetchall()
    return montar_cartoes(conexao, linhas)


def buscar_filmes(conexao, q, genero, ordem, pagina):
    """A listagem paginada de /filmes, com busca, filtro e ordenacao."""
    condicoes, parametros = [], []
    if q:
        condicoes.append("(f.titulo_busca LIKE ? OR f.titulo LIKE ?)")
        parametros += [f"%{q}%", f"%{q}%"]
    if genero:
        condicoes.append(
            "EXISTS (SELECT 1 FROM filme_categoria fc JOIN categoria c ON c.id = fc.categoria_id"
            " WHERE fc.filme_id = f.id AND c.nome = ?)"
        )
        parametros.append(genero)
    if ordem == "nota":
        condicoes.append("e.qtd >= ?")
        parametros.append(MIN_AVALIACOES)

    onde = ("WHERE " + " AND ".join(condicoes)) if condicoes else ""
    total = conexao.execute(
        f"SELECT COUNT(*) FROM filme f JOIN filme_estatistica e ON e.filme_id = f.id {onde}",
        parametros,
    ).fetchone()[0]

    paginas = max(1, math.ceil(total / POR_PAGINA))
    pagina = min(max(1, pagina), paginas)

    linhas = conexao.execute(
        f"""
        {CAMPOS_CARTAO}
        {onde}
        ORDER BY {ORDENS[ordem][1]}
        LIMIT ? OFFSET ?
        """,
        parametros + [POR_PAGINA, (pagina - 1) * POR_PAGINA],
    ).fetchall()

    return montar_cartoes(conexao, linhas), total, pagina, paginas


def lista_categorias(conexao):
    """Os generos com quantos filmes cada um tem."""
    return conexao.execute(
        """
        SELECT c.nome, COUNT(*) AS filmes
        FROM categoria c
        JOIN filme_categoria fc ON fc.categoria_id = c.id
        GROUP BY c.nome
        ORDER BY filmes DESC
        """
    ).fetchall()


def numeros_gerais(conexao):
    return conexao.execute(
        """
        SELECT (SELECT COUNT(*) FROM filme)      AS filmes,
               (SELECT COUNT(*) FROM avaliacao)  AS avaliacoes,
               (SELECT COUNT(*) FROM usuario)    AS usuarios,
               (SELECT AVG(nota) FROM avaliacao) AS media
        """
    ).fetchone()


def distribuicao_geral(conexao):
    """A distribuicao 1-5 de todas as avaliacoes da base."""
    linhas = conexao.execute(
        "SELECT nota, COUNT(*) AS qtd FROM avaliacao GROUP BY nota ORDER BY nota"
    ).fetchall()
    total = sum(linha["qtd"] for linha in linhas) or 1
    return [
        {"nota": linha["nota"], "qtd": linha["qtd"], "fatia": linha["qtd"] / total * 100}
        for linha in linhas
    ]
