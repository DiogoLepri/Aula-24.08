# -*- coding: utf-8 -*-
"""Catalogo do MovieLens 100k.

    uvicorn src.api.app:app --reload
"""

import math
import os
import sqlite3

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
BANCO = os.environ.get("MOVIELENS_DB", os.path.join(RAIZ, "movielens.db"))

POR_PAGINA = 24
MIN_AVALIACOES = 30

ORDENS = {
    "avaliados": ("mais avaliados", "e.qtd DESC, f.titulo_busca"),
    "nota": ("melhor nota", "e.media DESC, e.qtd DESC"),
    "ano": ("mais recentes", "f.ano DESC, f.titulo_busca"),
    "titulo": ("titulo A-Z", "f.titulo_busca"),
}

app = FastAPI(title="MovieLens 100k")
app.mount("/static", StaticFiles(directory=os.path.join(AQUI, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(AQUI, "templates"))


def banco():
    conexao = sqlite3.connect(BANCO)
    conexao.row_factory = sqlite3.Row
    try:
        yield conexao
    finally:
        conexao.close()


def perfil(linha):
    contagens = [linha["n1"], linha["n2"], linha["n3"], linha["n4"], linha["n5"]]
    total = sum(contagens) or 1
    return [
        {"nota": i + 1, "qtd": qtd, "fatia": qtd / total * 100}
        for i, qtd in enumerate(contagens)
    ]


def categorias_de(conexao, filme_ids):
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


def buscar_filmes(conexao, q, genero, ordem, pagina):
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
        SELECT f.id, f.titulo, f.titulo_busca, f.ano, f.poster, e.qtd, e.media,
               e.n1, e.n2, e.n3, e.n4, e.n5
        FROM filme f
        JOIN filme_estatistica e ON e.filme_id = f.id
        {onde}
        ORDER BY {ORDENS[ordem][1]}
        LIMIT ? OFFSET ?
        """,
        parametros + [POR_PAGINA, (pagina - 1) * POR_PAGINA],
    ).fetchall()

    por_filme = categorias_de(conexao, [linha["id"] for linha in linhas])
    filmes = [
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
    return filmes, total, pagina, paginas


def lista_categorias(conexao):
    return conexao.execute(
        """
        SELECT c.nome, COUNT(*) AS filmes
        FROM categoria c
        JOIN filme_categoria fc ON fc.categoria_id = c.id
        GROUP BY c.nome
        ORDER BY filmes DESC
        """
    ).fetchall()


@app.get("/", response_class=HTMLResponse)
def home(request: Request, conexao: sqlite3.Connection = Depends(banco)):
    numeros = conexao.execute(
        """
        SELECT (SELECT COUNT(*) FROM filme)     AS filmes,
               (SELECT COUNT(*) FROM avaliacao) AS avaliacoes,
               (SELECT COUNT(*) FROM usuario)   AS usuarios,
               (SELECT AVG(nota) FROM avaliacao) AS media
        """
    ).fetchone()

    distribuicao = conexao.execute(
        "SELECT nota, COUNT(*) AS qtd FROM avaliacao GROUP BY nota ORDER BY nota"
    ).fetchall()
    total_notas = sum(linha["qtd"] for linha in distribuicao) or 1
    perfil_geral = [
        {"nota": linha["nota"], "qtd": linha["qtd"], "fatia": linha["qtd"] / total_notas * 100}
        for linha in distribuicao
    ]

    periodo = conexao.execute(
        "SELECT MIN(avaliado_em) AS inicio, MAX(avaliado_em) AS fim FROM avaliacao"
    ).fetchone()

    mais_avaliados, _, _, _ = buscar_filmes(conexao, None, None, "avaliados", 1)
    melhores, _, _, _ = buscar_filmes(conexao, None, None, "nota", 1)

    estante = conexao.execute(
        """
        SELECT f.id, f.poster, f.titulo_busca
        FROM filme f
        JOIN filme_estatistica e ON e.filme_id = f.id
        WHERE f.poster IS NOT NULL
        ORDER BY e.qtd DESC
        LIMIT 10
        """
    ).fetchall()

    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "numeros": numeros,
            "estante": estante,
            "perfil_geral": perfil_geral,
            "periodo": periodo,
            "categorias": lista_categorias(conexao),
            "mais_avaliados": mais_avaliados[:6],
            "melhores": melhores[:6],
            "min_avaliacoes": MIN_AVALIACOES,
        },
    )


@app.get("/filmes", response_class=HTMLResponse)
def listagem(
    request: Request,
    q: str = Query(None, description="trecho do titulo"),
    genero: str = Query(None),
    ordem: str = Query("avaliados"),
    pagina: int = Query(1, ge=1),
    conexao: sqlite3.Connection = Depends(banco),
):
    if ordem not in ORDENS:
        ordem = "avaliados"
    filmes, total, pagina, paginas = buscar_filmes(conexao, q, genero, ordem, pagina)
    return templates.TemplateResponse(
        request,
        "filmes.html",
        {
            "filmes": filmes,
            "total": total,
            "pagina": pagina,
            "paginas": paginas,
            "q": q or "",
            "genero": genero or "",
            "ordem": ordem,
            "ordens": ORDENS,
            "categorias": lista_categorias(conexao),
            "min_avaliacoes": MIN_AVALIACOES,
        },
    )


@app.get("/filmes/{filme_id}", response_class=HTMLResponse)
def detalhe(
    request: Request,
    filme_id: int,
    conexao: sqlite3.Connection = Depends(banco),
):
    linha = conexao.execute(
        """
        SELECT f.*, e.qtd, e.media, e.n1, e.n2, e.n3, e.n4, e.n5
        FROM filme f
        JOIN filme_estatistica e ON e.filme_id = f.id
        WHERE f.id = ?
        """,
        (filme_id,),
    ).fetchone()

    if linha is None:
        return templates.TemplateResponse(
            request, "nao_encontrado.html", {"filme_id": filme_id}, status_code=404
        )

    equipe = conexao.execute(
        """
        SELECT p.nome, p.foto, fp.papel, fp.ordem
        FROM filme_pessoa fp
        JOIN pessoa p ON p.id = fp.pessoa_id
        WHERE fp.filme_id = ?
        ORDER BY fp.papel, COALESCE(fp.ordem, 0)
        """,
        (filme_id,),
    ).fetchall()

    por_sexo = conexao.execute(
        """
        SELECT u.sexo, COUNT(*) AS qtd, AVG(a.nota) AS media
        FROM avaliacao a
        JOIN usuario u ON u.id = a.usuario_id
        WHERE a.filme_id = ?
        GROUP BY u.sexo
        """,
        (filme_id,),
    ).fetchall()

    categorias = [
        registro["nome"]
        for registro in conexao.execute(
            """
            SELECT c.nome FROM filme_categoria fc
            JOIN categoria c ON c.id = fc.categoria_id
            WHERE fc.filme_id = ? ORDER BY c.nome
            """,
            (filme_id,),
        )
    ]

    return templates.TemplateResponse(
        request,
        "filme.html",
        {
            "filme": linha,
            "categorias": categorias,
            "perfil": perfil(linha),
            "diretores": [p for p in equipe if p["papel"] == "diretor"],
            "atores": [p for p in equipe if p["papel"] == "ator"],
            "por_sexo": {p["sexo"]: p for p in por_sexo},
        },
    )


@app.get("/api/filmes")
def api_filmes(
    q: str = Query(None),
    genero: str = Query(None),
    ordem: str = Query("avaliados"),
    pagina: int = Query(1, ge=1),
    conexao: sqlite3.Connection = Depends(banco),
):
    """Mesma listagem, em JSON."""
    if ordem not in ORDENS:
        ordem = "avaliados"
    filmes, total, pagina, paginas = buscar_filmes(conexao, q, genero, ordem, pagina)
    return {"total": total, "pagina": pagina, "paginas": paginas, "filmes": filmes}
