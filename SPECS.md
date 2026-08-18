# SPECS — Catálogo MovieLens 100k

Catálogo web do conjunto [MovieLens 100k](https://grouplens.org/datasets/movielens/100k/)
(100.000 avaliações, 943 usuários, 1.682 filmes, coletadas pelo GroupLens entre
setembro de 1997 e abril de 1998), enriquecido com elenco, direção, pôsteres e
fotos vindos do [TMDB](https://www.themoviedb.org). Trabalho acadêmico, sem uso
comercial; o TMDB não endossa este projeto.

## Escopo

- Base de dados com **filme, categorias, atores e diretor** (SQLite)
- **Design da página** (templates Jinja2 + CSS próprio)
- **Script de scraping** (TMDB, com pôster e foto do elenco)
- **FastAPI básico**, com home, listagem e detalhe
- **SPECS em markdown** (este arquivo)

## Estrutura do projeto

| Caminho | Papel |
|---|---|
| `carga.py` | Cria o banco do zero a partir dos arquivos do ml-100k |
| `scraper.py` | Completa o banco com elenco, direção e imagens via TMDB |
| `app.py` | Aplicação FastAPI (páginas HTML + API JSON) |
| `analise_movielens.py` | Análise exploratória em texto, com foco nas categorias |
| `templates/` | Jinja2: `base.html`, `home.html`, `filmes.html`, `filme.html`, `nao_encontrado.html` |
| `static/estilo.css` | Todo o estilo do site |
| `requirements.txt` | Dependências |

O banco (`movielens.db`) e o dataset (`ml-100k/`) não são versionados — ver
`.gitignore`. Cada um é reproduzível pelos scripts acima.

## Como rodar

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. carga: procura o ml-100k na pasta do projeto, em ./ml-100k e em ~/Downloads/ml-100k
python carga.py --dados ~/Downloads/ml-100k

# 2. scraping (opcional, mas necessário para elenco e imagens)
export TMDB_API_KEY=sua_chave        # themoviedb.org/settings/api
python scraper.py                    # ou --simular para testar sem chave

# 3. aplicação
uvicorn app:app --reload             # http://127.0.0.1:8000
```

## Banco de dados

SQLite, esquema criado por `carga.py` (apaga e recria as tabelas a cada execução):

- **filme** — id (o MovieID original), titulo (bruto do ml-100k), titulo_busca
  (normalizado: artigo de volta ao início, sem ano), titulo_alt, ano,
  data_lancamento (ISO), imdb_url, **poster** (caminho de imagem no TMDB)
- **categoria** — os 19 gêneros de `u.genre`
- **filme_categoria** — N:N filme × categoria
- **pessoa** — nome (único), tmdb_id, **foto** (caminho de imagem no TMDB)
- **filme_pessoa** — N:N com `papel` (`ator` | `diretor`) e `ordem` de crédito
- **usuario** — id, idade, sexo (M/F), ocupacao, cep
- **avaliacao** — usuario × filme, nota 1–5, timestamp; PK (usuario, filme)
- **filme_estatistica** — agregados pré-calculados por filme: qtd, média e a
  contagem por nota (n1..n5), que alimenta as barras de distribuição do site
- **scraper_log** — progresso do scraper por filme (`ok`, `nao_encontrado`,
  `sem_creditos`), o que permite retomar a coleta de onde parou

Pessoa e filme_pessoa nascem vazias: o ml-100k não traz elenco nem direção em
lugar nenhum — quem preenche é o scraper.

## Scraper (TMDB)

A URL do IMDb em `u.item` é um link de busca de 1998, sem identificador `tt`,
então o casamento com o TMDB é feito por **título e ano**: tenta o ano exato,
depois ±1 ano, depois sem ano; se falhar, tenta o título alternativo. Do filme
encontrado guarda o `poster_path`; dos créditos, o diretor e os 8 primeiros
atores em ordem de crédito, cada um com `profile_path` (foto) quando o TMDB
tem.

Flags principais: `--simular` (nomes falsos, sem chave, para testar a
interface), `--refazer` (recomeça do zero, apagando pessoas e pôsteres),
`--limite N`, `--elenco N`, `--pausa s`. Respeita `Retry-After` em 429 e
grava o progresso em `scraper_log` a cada filme.

Cobertura obtida: 1.670 dos 1.682 filmes com créditos (99,3%). Os 12 restantes
são títulos que a busca do TMDB não resolve (grafias erradas no próprio
MovieLens, minisséries, filmes catalogados por outro nome) e aparecem no site
com a mensagem de "ainda não coletado".

## Aplicação (FastAPI)

| Rota | Resposta |
|---|---|
| `GET /` | Home: números gerais da base, distribuição de todas as notas, estante de pôsteres, mais avaliados, melhores notas, gêneros |
| `GET /filmes` | Listagem com busca por título (`q`), filtro por gênero (`genero`), ordenação (`ordem`: avaliados, nota, ano, titulo) e paginação (`pagina`, 24 por página) |
| `GET /filmes/{id}` | Detalhe: pôster, gêneros clicáveis, distribuição de notas, recorte por sexo, elenco e direção com fotos; 404 amigável se o id não existe |
| `GET /api/filmes` | A mesma listagem, em JSON (mesmos parâmetros) |
| `GET /static/*` | Arquivos estáticos |

A ordenação por **nota** exige um mínimo de 30 avaliações (`MIN_AVALIACOES`) —
sem esse piso, o topo vira uma fila de filmes com três notas 5. A home explica
o critério.

## Design

Identidade: fundo de papel quente, display **Bricolage Grotesque**, texto
**Public Sans**, números em **IBM Plex Mono**, acento terracota. A distribuição
de notas (1–5) aparece como barra empilhada colorida em todos os cards e no
detalhe. Imagens vêm da CDN do TMDB (`image.tmdb.org`); filmes sem pôster e
pessoas sem foto recebem um placeholder tipográfico. Estados de hover e foco
visíveis, `prefers-reduced-motion` respeitado, layout responsivo.

## Limitações conhecidas

- 12 filmes sem elenco/pôster (casos de casamento de título descritos acima).
- O ml-100k tem títulos duplicados (o mesmo filme com dois MovieIDs), então as
  notas de um mesmo filme podem estar divididas em mais de um registro.
  `carga.py` conta 23 duplicatas comparando o título normalizado;
  `analise_movielens.py` conta 18 comparando o título bruto.
- As imagens dependem da CDN do TMDB estar acessível.
