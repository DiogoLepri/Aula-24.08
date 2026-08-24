-- Esquema do catalogo MovieLens 100k.
--
-- O centro e filme. Em volta dele, as quatro coisas que o quadro pede:
--
--     categoria  --<  filme_categoria  >--  FILME  --<  filme_pessoa  >--  pessoa
--                                             |                            (atores
--                                             |                          e diretores)
--                                        avaliacao  >--  usuario
--
-- Ligacoes N:N ficam em tabela propria (filme_categoria, filme_pessoa) e a
-- nota mora na avaliacao, que e a ponte entre usuario e filme.
--
-- Rodar este arquivo APAGA e recria tudo: e o que src/data/carga.py faz a
-- cada carga do ml-100k.

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS filme_estatistica;
DROP TABLE IF EXISTS avaliacao;
DROP TABLE IF EXISTS filme_pessoa;
DROP TABLE IF EXISTS filme_categoria;
DROP TABLE IF EXISTS pessoa;
DROP TABLE IF EXISTS categoria;
DROP TABLE IF EXISTS usuario;
DROP TABLE IF EXISTS filme;

-- FILME -----------------------------------------------------------------
-- id e o MovieID original do ml-100k. titulo e o texto bruto do dataset;
-- titulo_busca e a versao normalizada (artigo de volta ao inicio, sem ano),
-- que e a usada na tela e na busca. poster vem do TMDB, pelo scraper.
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

-- CATEGORIAS ------------------------------------------------------------
-- Os 19 generos de u.genre. Um filme pode estar em varios.
CREATE TABLE categoria (
    id   INTEGER PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE
);

CREATE TABLE filme_categoria (
    filme_id     INTEGER NOT NULL REFERENCES filme(id),
    categoria_id INTEGER NOT NULL REFERENCES categoria(id),
    PRIMARY KEY (filme_id, categoria_id)
);

-- ATORES E DIRETORES ----------------------------------------------------
-- Nascem vazias: o ml-100k nao traz elenco nem direcao em lugar nenhum.
-- Quem preenche e src/services/scraper.py, com dados do TMDB.
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

-- USUARIO ---------------------------------------------------------------
CREATE TABLE usuario (
    id       INTEGER PRIMARY KEY,
    idade    INTEGER,
    sexo     TEXT CHECK (sexo IN ('M', 'F')),
    ocupacao TEXT,
    cep      TEXT
);

-- AVALIACAO -------------------------------------------------------------
-- A ponte usuario x filme. Cada pessoa da no maximo uma nota por filme.
CREATE TABLE avaliacao (
    usuario_id  INTEGER NOT NULL REFERENCES usuario(id),
    filme_id    INTEGER NOT NULL REFERENCES filme(id),
    nota        INTEGER NOT NULL CHECK (nota BETWEEN 1 AND 5),
    avaliado_em INTEGER NOT NULL,
    PRIMARY KEY (usuario_id, filme_id)
);

-- ESTATISTICA -----------------------------------------------------------
-- Agregado por filme, calculado uma vez na carga: quantidade, media e a
-- contagem por nota (n1..n5) que desenha as barras do site. Existe para o
-- top 10 e as listagens nao varrerem as 100 mil avaliacoes a cada pagina.
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
