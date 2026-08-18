# -*- coding: utf-8 -*-
"""Completa o banco com atores e diretor, que o ml-100k nao traz.

    export TMDB_API_KEY=sua_chave
    python scraper.py --banco movielens.db

A URL do IMDb em u.item nao serve como identificador: e um link de busca de
1998, sem o id tt. O casamento e feito por titulo e ano contra o TMDB.
"""

import argparse
import os
import sqlite3
import sys
import time

import requests

BASE = "https://api.themoviedb.org/3"
ELENCO_PADRAO = 8

LOG = """
CREATE TABLE IF NOT EXISTS scraper_log (
    filme_id INTEGER PRIMARY KEY REFERENCES filme(id),
    status   TEXT NOT NULL,
    tmdb_id  INTEGER,
    quando   TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


class TMDB:
    def __init__(self, chave, pausa=0.25):
        self.chave = chave
        self.pausa = pausa
        self.sessao = requests.Session()

    def pedir(self, caminho, **parametros):
        parametros["api_key"] = self.chave
        for tentativa in range(4):
            time.sleep(self.pausa)
            try:
                resposta = self.sessao.get(f"{BASE}{caminho}", params=parametros, timeout=20)
            except requests.RequestException as erro:
                if tentativa == 3:
                    raise
                print(f"    rede falhou ({erro}); tentando de novo", file=sys.stderr)
                time.sleep(2 ** tentativa)
                continue

            if resposta.status_code == 401:
                sys.exit("Chave do TMDB recusada (401). Confira TMDB_API_KEY ou --chave.")
            if resposta.status_code == 429:
                espera = int(resposta.headers.get("Retry-After", 5))
                print(f"    limite de requisicoes; esperando {espera}s", file=sys.stderr)
                time.sleep(espera)
                continue
            if resposta.status_code == 404:
                return None
            resposta.raise_for_status()
            return resposta.json()
        return None

    def procurar(self, titulo, ano):
        """Tenta o ano exato, depois mais ou menos 1, depois sem ano."""
        tentativas = [{"primary_release_year": ano}] if ano else []
        if ano:
            tentativas += [{"primary_release_year": ano - 1}, {"primary_release_year": ano + 1}]
        tentativas.append({})

        for extra in tentativas:
            dados = self.pedir("/search/movie", query=titulo, include_adult="false", **extra)
            resultados = (dados or {}).get("results") or []
            if resultados:
                return resultados[0]
        return None

    def creditos(self, tmdb_id):
        return self.pedir(f"/movie/{tmdb_id}/credits")


def creditos_simulados(filme_id, titulo, elenco):
    """Preenche nomes obviamente falsos, so para testar a interface sem chave."""
    return {
        "crew": [{"job": "Director", "name": f"Diretor Exemplo {filme_id}"}],
        "cast": [
            {"name": f"Ator Exemplo {filme_id}-{i + 1}", "order": i} for i in range(elenco)
        ],
    }


def gravar(conexao, filme_id, creditos, elenco):
    entradas = []

    for membro in creditos.get("crew") or []:
        if membro.get("job") == "Director" and membro.get("name"):
            entradas.append(
                (membro["name"].strip(), "diretor", None,
                 membro.get("profile_path"), membro.get("id"))
            )

    for membro in sorted(creditos.get("cast") or [], key=lambda m: m.get("order", 999))[:elenco]:
        if membro.get("name"):
            entradas.append(
                (membro["name"].strip(), "ator", membro.get("order"),
                 membro.get("profile_path"), membro.get("id"))
            )

    for nome, papel, ordem, foto, tmdb_pessoa in entradas:
        conexao.execute("INSERT OR IGNORE INTO pessoa (nome) VALUES (?)", (nome,))
        conexao.execute(
            "UPDATE pessoa SET foto = COALESCE(foto, ?), tmdb_id = COALESCE(tmdb_id, ?)"
            " WHERE nome = ?",
            (foto, tmdb_pessoa, nome),
        )
        pessoa_id = conexao.execute("SELECT id FROM pessoa WHERE nome = ?", (nome,)).fetchone()[0]
        conexao.execute(
            "INSERT OR IGNORE INTO filme_pessoa (filme_id, pessoa_id, papel, ordem)"
            " VALUES (?, ?, ?, ?)",
            (filme_id, pessoa_id, papel, ordem),
        )
    return len(entradas)


def rodar(argumentos):
    if not os.path.exists(argumentos.banco):
        sys.exit(f"Banco {argumentos.banco} nao existe. Rode o carga.py primeiro.")

    chave = argumentos.chave or os.environ.get("TMDB_API_KEY")
    if not chave and not argumentos.simular:
        sys.exit(
            "Falta a chave do TMDB.\n"
            "  export TMDB_API_KEY=sua_chave   (pegue em themoviedb.org/settings/api)\n"
            "Ou rode com --simular para preencher nomes falsos e testar a interface."
        )

    conexao = sqlite3.connect(argumentos.banco)
    conexao.executescript(LOG)

    if argumentos.refazer:
        conexao.execute("DELETE FROM scraper_log")
        conexao.execute("DELETE FROM filme_pessoa")
        conexao.execute("DELETE FROM pessoa")
        conexao.execute("UPDATE filme SET poster = NULL")
        conexao.commit()

    pendentes = conexao.execute(
        """
        SELECT f.id, f.titulo_busca, f.titulo_alt, f.ano
        FROM filme f
        LEFT JOIN scraper_log l ON l.filme_id = f.id
        WHERE l.filme_id IS NULL
        ORDER BY f.id
        """
    ).fetchall()

    if argumentos.limite:
        pendentes = pendentes[: argumentos.limite]

    total = len(pendentes)
    if not total:
        print("Nada pendente - todos os filmes ja passaram pelo scraper.")
        print("Use --refazer para comecar do zero.")
        return

    if argumentos.simular:
        print("MODO SIMULACAO: os nomes gravados sao falsos, so para testar a interface.\n")

    api = None if argumentos.simular else TMDB(chave, argumentos.pausa)
    encontrados = falhas = 0

    print(f"{total} filmes pendentes.\n")
    for posicao, (filme_id, titulo, alternativo, ano) in enumerate(pendentes, 1):
        rotulo = f"[{posicao}/{total}] {titulo} ({ano or 's/ano'})"

        if argumentos.simular:
            creditos = creditos_simulados(filme_id, titulo, argumentos.elenco)
            tmdb_id = None
        else:
            achado = api.procurar(titulo, ano)
            if achado is None and alternativo:
                achado = api.procurar(alternativo, ano)
            if achado is None:
                conexao.execute(
                    "INSERT OR REPLACE INTO scraper_log (filme_id, status) VALUES (?, ?)",
                    (filme_id, "nao_encontrado"),
                )
                conexao.commit()
                falhas += 1
                print(f"{rotulo} - nao encontrado")
                continue
            tmdb_id = achado["id"]
            if achado.get("poster_path"):
                conexao.execute(
                    "UPDATE filme SET poster = ? WHERE id = ?",
                    (achado["poster_path"], filme_id),
                )
            creditos = api.creditos(tmdb_id) or {}

        quantos = gravar(conexao, filme_id, creditos, argumentos.elenco)
        conexao.execute(
            "INSERT OR REPLACE INTO scraper_log (filme_id, status, tmdb_id) VALUES (?, ?, ?)",
            (filme_id, "ok" if quantos else "sem_creditos", tmdb_id),
        )
        conexao.commit()

        if quantos:
            encontrados += 1
            print(f"{rotulo} - {quantos} nomes")
        else:
            falhas += 1
            print(f"{rotulo} - sem creditos no TMDB")

    pessoas = conexao.execute("SELECT COUNT(*) FROM pessoa").fetchone()[0]
    vinculos = conexao.execute("SELECT COUNT(*) FROM filme_pessoa").fetchone()[0]
    conexao.close()

    print(f"\n{encontrados} filmes completados, {falhas} sem resultado.")
    print(f"Banco agora tem {pessoas} pessoas e {vinculos} vinculos filme-pessoa.")
    if falhas:
        print("Rode de novo depois para tentar so os que faltam (o log guarda o progresso).")


def main():
    parser = argparse.ArgumentParser(description="Completa atores e diretor via TMDB.")
    parser.add_argument("--banco", default="movielens.db")
    parser.add_argument("--chave", help="chave do TMDB (ou use a variavel TMDB_API_KEY)")
    parser.add_argument("--elenco", type=int, default=ELENCO_PADRAO,
                        help=f"quantos atores por filme (padrao {ELENCO_PADRAO})")
    parser.add_argument("--limite", type=int, help="processa so os N primeiros pendentes")
    parser.add_argument("--pausa", type=float, default=0.25,
                        help="segundos entre requisicoes (padrao 0,25)")
    parser.add_argument("--simular", action="store_true",
                        help="preenche nomes falsos, sem chamar a API")
    parser.add_argument("--refazer", action="store_true",
                        help="apaga o que ja foi coletado e recomeca")
    rodar(parser.parse_args())


if __name__ == "__main__":
    main()
