# -*- coding: utf-8 -*-
"""Catalogo do MovieLens 100k.

    uvicorn src.api.app:app --reload

As rotas so juntam o que src/data/consultas.py le do banco e o que
src/recommenders/ escolhe para a home, e entregam ao template.
"""

import os
import sqlite3

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.data import consultas
from src.data.banco import conexao_web
from src.recommenders import prateleiras

AQUI = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="MovieLens 100k")
app.mount("/static", StaticFiles(directory=os.path.join(AQUI, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(AQUI, "template"))


@app.get("/", response_class=HTMLResponse)
def home(request: Request, conexao: sqlite3.Connection = Depends(conexao_web)):
    """Numeros gerais da base, a estante de posteres e as prateleiras."""
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "numeros": consultas.numeros_gerais(conexao),
            "perfil_geral": consultas.distribuicao_geral(conexao),
            "estante": conexao.execute(
                """
                SELECT f.id, f.poster, f.titulo_busca
                FROM filme f
                JOIN filme_estatistica e ON e.filme_id = f.id
                WHERE f.poster IS NOT NULL
                ORDER BY e.qtd DESC
                LIMIT 10
                """
            ).fetchall(),
            "prateleiras": prateleiras(conexao),
            "categorias": consultas.lista_categorias(conexao),
            "min_avaliacoes": consultas.MIN_AVALIACOES,
        },
    )


@app.get("/filmes", response_class=HTMLResponse)
def listagem(
    request: Request,
    q: str = Query(None, description="trecho do titulo"),
    genero: str = Query(None),
    ordem: str = Query("avaliados"),
    pagina: int = Query(1, ge=1),
    conexao: sqlite3.Connection = Depends(conexao_web),
):
    if ordem not in consultas.ORDENS:
        ordem = "avaliados"
    filmes, total, pagina, paginas = consultas.buscar_filmes(conexao, q, genero, ordem, pagina)
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
            "ordens": consultas.ORDENS,
            "categorias": consultas.lista_categorias(conexao),
            "min_avaliacoes": consultas.MIN_AVALIACOES,
        },
    )


@app.get("/filmes/{filme_id}", response_class=HTMLResponse)
def detalhe(
    request: Request,
    filme_id: int,
    conexao: sqlite3.Connection = Depends(conexao_web),
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
            "perfil": consultas.perfil(linha),
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
    conexao: sqlite3.Connection = Depends(conexao_web),
):
    """Mesma listagem, em JSON."""
    if ordem not in consultas.ORDENS:
        ordem = "avaliados"
    filmes, total, pagina, paginas = consultas.buscar_filmes(conexao, q, genero, ordem, pagina)
    return {"total": total, "pagina": pagina, "paginas": paginas, "filmes": filmes}


@app.get("/api/prateleiras")
def api_prateleiras(
    limite: int = Query(10, ge=1, le=50),
    conexao: sqlite3.Connection = Depends(conexao_web),
):
    """As prateleiras da home, em JSON."""
    return {"prateleiras": prateleiras(conexao, limite)}
