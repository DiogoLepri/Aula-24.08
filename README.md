[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/E_InTkhT)

# Catálogo MovieLens 100k

Catálogo web do conjunto MovieLens 100k (100.000 avaliações, 943 usuários,
1.682 filmes), com elenco, direção, pôsteres e fotos vindos do TMDB.
FastAPI + SQLite + Jinja2.

A especificação completa — esquema do banco, rotas, scripts e decisões de
projeto — está em [SPECS.md](SPECS.md).

## Rodando

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python carga.py --dados ~/Downloads/ml-100k   # cria movielens.db a partir do dataset
export TMDB_API_KEY=sua_chave                 # themoviedb.org/settings/api
python scraper.py                             # elenco, direção e imagens (ou --simular)
uvicorn app:app --reload                      # http://127.0.0.1:8000
```

`analise_movielens.py` gera a análise exploratória da base em texto, no
terminal (requer pandas e os arquivos do ml-100k).
