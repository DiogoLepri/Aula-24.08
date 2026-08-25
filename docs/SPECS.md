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
- **SPECS em markdown** (este arquivo) e o esquema detalhado em `docs/esquema.md`

## Estrutura do projeto

```
docs/                 SPECS e esquema do banco
README.md
notebooks/            análise exploratória da base
src/
├── api/              aplicação FastAPI
│   ├── static/       CSS
│   └── template/     Jinja2
├── data/             esquema do banco, carga do ml-100k e consultas
├── recommenders/     as prateleiras da home (top 10, mais avaliados, aleatório)
└── services/         integrações externas (TMDB)
tests/                testes (só biblioteca padrão)
```

| Caminho | Papel |
|---|---|
| `src/data/esquema.sql` | O DDL: tabelas, chaves e índices |
| `src/data/banco.py` | Caminho do banco e abertura de conexão |
| `src/data/carga.py` | Cria o banco do zero a partir dos arquivos do ml-100k |
| `src/services/scraper.py` | Completa o banco com elenco, direção e imagens via TMDB |
| `src/api/app.py` | Aplicação FastAPI (páginas HTML + API JSON) |
| `src/api/template/` | Jinja2: `base.html`, `home.html`, `filmes.html`, `filme.html`, `nao_encontrado.html` |
| `src/api/static/estilo.css` | Todo o estilo do site |
| `src/data/consultas.py` | As consultas que a listagem e a home fazem no banco |
| `src/recommenders/` | Uma prateleira da home por módulo: `top10`, `populares`, `aleatorio` |
| `notebooks/analise_movielens.py` | Análise exploratória em texto, com foco nas categorias |
| `tests/` | Testes em `unittest`, sobre um banco em memória |
| `requirements.txt` | Dependências |

O banco (`movielens.db`) e o dataset (`ml-100k/`) não são versionados — ver
`.gitignore`. Cada um é reproduzível pelos scripts acima.

## Como rodar

Todos os comandos rodam a partir da raiz do projeto.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. carga: procura o ml-100k na raiz do projeto, em ./ml-100k e em ~/Downloads/ml-100k
python -m src.data.carga --dados ~/Downloads/ml-100k

# 2. scraping (opcional, mas necessário para elenco e imagens)
export TMDB_API_KEY=sua_chave        # themoviedb.org/settings/api
python -m src.services.scraper       # ou --simular para testar sem chave

# 3. aplicação
uvicorn src.api.app:app --reload     # http://127.0.0.1:8000
```

## Banco de dados

SQLite. O DDL fica em `src/data/esquema.sql` e é aplicado por
`src/data/carga.py`, que apaga e recria as tabelas a cada execução.
`src/data/banco.py` centraliza o caminho do arquivo e a abertura da conexão.

O diagrama e a explicação tabela por tabela estão em
**[docs/esquema.md](esquema.md)**. Em resumo, o centro é `filme`, e em volta
dele:

- **usuário** liga-se a filme por **avaliacao** (nota 1–5, PK usuário+filme)
- **categoria** liga-se a filme por **filme_categoria** (N:N, 19 gêneros)
- **pessoa** (atores e diretores) liga-se a filme por **filme_pessoa** (N:N,
  com `papel` e `ordem` de crédito)
- **filme_estatistica** guarda o agregado por filme — qtd, média e a contagem
  por nota (n1..n5) — calculado uma vez na carga, que é o que sustenta o top 10
  e as listagens sem varrer as 100 mil avaliações
- **scraper_log** guarda o progresso do scraper por filme, o que permite
  retomar a coleta de onde parou

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
| `GET /` | Home: números gerais da base, distribuição de todas as notas, estante de pôsteres, as três prateleiras e os gêneros |
| `GET /filmes` | Listagem com busca por título (`q`), filtro por gênero (`genero`), ordenação (`ordem`: avaliados, nota, ano, titulo) e paginação (`pagina`, 24 por página) |
| `GET /filmes/{id}` | Detalhe: pôster, gêneros clicáveis, distribuição de notas, recorte por sexo, elenco e direção com fotos; 404 amigável se o id não existe |
| `GET /api/filmes` | A mesma listagem, em JSON (mesmos parâmetros) |
| `GET /api/prateleiras` | As prateleiras da home, em JSON (`limite`, 1–50) |
| `GET /static/*` | Arquivos estáticos |

A ordenação por **nota** exige um mínimo de 30 avaliações (`MIN_AVALIACOES`) —
sem esse piso, o topo vira uma fila de filmes com três notas 5. A home explica
o critério.

### As prateleiras da home

Cada uma é um módulo em `src/recommenders/`, todos com a mesma forma (`NOME`,
`TITULO`, `LINK`, `linha()` e `selecionar(conexao, limite)`), e a home monta o
que estiver na tupla `PRATELEIRAS`. São dez filmes por prateleira, numa fileira
que rola de lado:

| Prateleira | Critério |
|---|---|
| **Top 10** | Maior média, entre os filmes com pelo menos `MIN_AVALIACOES` avaliações |
| **Os mais avaliados** | Maior número de avaliações — volume, não nota |
| **Aleatório** | `ORDER BY RANDOM()` entre os filmes com alguma avaliação; muda a cada visita |

Acrescentar uma prateleira é escrever o módulo e pô-lo na tupla — a home e o
`/api/prateleiras` passam a mostrá-la sem mais nenhuma mudança.

## Design

Visual de serviço de streaming — a referência é a Netflix, e a escolha não é
só estética: o catálogo é uma lista de filmes com pôster, que é exatamente o
que esse desenho resolve bem.

- **Cor:** fundo `#141414`, superfícies `#1f1f1f`, texto branco sobre cinza
  `#b3b3b3`, acento vermelho `#e50914`. Verde `#46d369` só para o percentual
  de aprovação.
- **Tipografia:** Inter, do 400 ao 900. Títulos em 900 com `letter-spacing`
  negativo; números com `tabular-nums` para as colunas não dançarem.
- **Abertura:** o filme mais avaliado da base ocupa a tela inteira, com o
  pôster desfocado e ampliado como fundo, dois véus de gradiente por cima e o
  texto à esquerda. O topo é transparente sobre ele e escurece ao rolar
  (única linha de JavaScript do site).
- **Cartão:** o pôster manda. De pé, só o título sobre um gradiente; no hover
  ou no foco o cartão cresce 5% e revela aprovação, ano, a barra de
  distribuição, a média e os gêneros.
- **Prateleiras:** fileira que rola de lado, dez por vez, com `scroll-snap`.
  Nas duas que são ranking, o numerão vai atrás do pôster, vazado, com o `1`
  em vermelho — `scroll-padding` alinha o primeiro cartão com o título da
  seção.
- **O número verde:** a média sozinha achata a diferença entre um filme que
  todo mundo achou bom e um que metade amou. O cartão mostra a **fatia de
  notas 4 e 5** (`consultas.aprovacao`), que é o que a base tem de mais
  próximo de um "% de quem gostou". A média continua ali, ao lado.

A distribuição de notas (1–5) segue como barra empilhada colorida em todos os
cartões e no detalhe — é o dado do trabalho, e o visual escuro só mudou as
cores dela. Imagens vêm da CDN do TMDB (`image.tmdb.org`); filmes sem pôster e
pessoas sem foto recebem um placeholder tipográfico. Estados de hover e foco
visíveis, `prefers-reduced-motion` respeitado, layout responsivo (no celular
as fileiras viram grade).

## Limitações conhecidas

- 12 filmes sem elenco/pôster (casos de casamento de título descritos acima).
- O ml-100k tem títulos duplicados (o mesmo filme com dois MovieIDs), então as
  notas de um mesmo filme podem estar divididas em mais de um registro.
  `src/data/carga.py` conta 23 duplicatas comparando o título normalizado;
  `notebooks/analise_movielens.py` conta 18 comparando o título bruto.
- As imagens dependem da CDN do TMDB estar acessível.
