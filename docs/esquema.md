# Esquema do banco

SQLite. O DDL está em [`src/data/esquema.sql`](../src/data/esquema.sql) e é
aplicado por `src/data/carga.py` a cada carga do ml-100k (apaga e recria tudo).

## O desenho

O centro é **filme**. Em volta dele, as quatro coisas do catálogo: quem
avaliou (**usuário**), o que ele é (**categorias**) e quem fez (**atores** e
diretores).

![DER do catálogo MovieLens 100k](der.svg)

O mesmo diagrama em Mermaid, para quem quiser editar:

```mermaid
erDiagram
    USUARIO   ||--o{ AVALIACAO       : "dá nota"
    FILME     ||--o{ AVALIACAO       : "recebe nota"
    FILME     ||--o{ FILME_CATEGORIA : ""
    CATEGORIA ||--o{ FILME_CATEGORIA : ""
    FILME     ||--o{ FILME_PESSOA    : ""
    PESSOA    ||--o{ FILME_PESSOA    : "ator ou diretor"
    FILME     ||--|| FILME_ESTATISTICA : "agregado"

    FILME {
        int  id PK "MovieID do ml-100k"
        text titulo "bruto do dataset"
        text titulo_busca "normalizado, é o que aparece na tela"
        text titulo_alt
        int  ano
        text data_lancamento "ISO"
        text imdb_url
        text poster "caminho de imagem no TMDB"
    }
    USUARIO {
        int  id PK
        int  idade
        text sexo "M ou F"
        text ocupacao
        text cep
    }
    AVALIACAO {
        int usuario_id PK,FK
        int filme_id PK,FK
        int nota "1 a 5"
        int avaliado_em "timestamp"
    }
    CATEGORIA {
        int  id PK
        text nome "os 19 gêneros de u.genre"
    }
    FILME_CATEGORIA {
        int filme_id PK,FK
        int categoria_id PK,FK
    }
    PESSOA {
        int  id PK
        text nome UK
        int  tmdb_id
        text foto "caminho de imagem no TMDB"
    }
    FILME_PESSOA {
        int  filme_id PK,FK
        int  pessoa_id PK,FK
        text papel PK "ator ou diretor"
        int  ordem "posição no crédito"
    }
    FILME_ESTATISTICA {
        int  filme_id PK,FK
        int  qtd
        real media
        int  n1
        int  n2
        int  n3
        int  n4
        int  n5
    }
```

## Tabela por tabela

| Tabela | O que guarda | De onde vem |
|---|---|---|
| `filme` | 1.682 filmes: título, ano, link do IMDb, pôster | `u.item` (+ pôster do TMDB) |
| `categoria` | Os 19 gêneros | `u.genre` |
| `filme_categoria` | N:N filme × gênero — um filme pode ter vários | `u.item` |
| `pessoa` | Atores e diretores, com foto | TMDB, via scraper |
| `filme_pessoa` | N:N filme × pessoa, com `papel` e `ordem` de crédito | TMDB, via scraper |
| `usuario` | 943 usuários: idade, sexo, ocupação, CEP | `u.user` |
| `avaliacao` | 100.000 notas de 1 a 5, PK (usuário, filme) | `u.data` |
| `filme_estatistica` | Agregado por filme: qtd, média e contagem por nota | calculado na carga |
| `scraper_log` | Progresso do scraper por filme, para retomar de onde parou | criado pelo scraper |

## Três decisões

**As ligações N:N ficam em tabela própria.** Um filme está em vários gêneros e
tem vários atores; um ator está em vários filmes. `filme_categoria` e
`filme_pessoa` são só os pares. Em `filme_pessoa`, `papel` faz parte da chave —
a mesma pessoa pode dirigir e atuar no mesmo filme.

**`filme_estatistica` é redundante de propósito.** Média e contagem por nota
dão para calcular a partir de `avaliacao`, mas o top 10 e cada página da
listagem teriam que varrer 100 mil linhas. Como a base é fechada (não entra
avaliação nova), o agregado é calculado uma vez, na carga.

**`pessoa` e `filme_pessoa` nascem vazias.** O ml-100k não traz elenco nem
direção em lugar nenhum — nem no `u.item`, nem em arquivo separado. Quem
preenche é `src/services/scraper.py`, casando título e ano contra o TMDB.

## Conferindo um banco já criado

```bash
sqlite3 movielens.db ".schema"
sqlite3 movielens.db "SELECT COUNT(*) FROM filme, avaliacao, usuario;"
```
