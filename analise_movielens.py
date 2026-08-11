# -*- coding: utf-8 -*-
"""Análise exploratória do MovieLens 1M, com foco nas categorias.

Requer pandas e numpy, além dos arquivos ratings.dat, users.dat e movies.dat
na mesma pasta. Toda a saída é em texto corrido, no terminal.

Sobre as métricas: a única medida de nota usada aqui é a média. Todo o resto do
relatório é contagem e participação percentual — quantos filmes, quantas
avaliações, quantos usuários, que fatia do total cada categoria representa. A
nota metodológica no fim explica o que ficou de fora e por quê.
"""

import os
import textwrap

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LARGURA = 88

MIN_FILME = 100    # avaliações mínimas para entrar em ranking de nota do catálogo
MIN_GENERO = 50    # idem, para rankings de nota dentro de um gênero

FAIXAS_ETARIAS = {
    1: "Menor de 18",
    18: "18-24",
    25: "25-34",
    35: "35-44",
    45: "45-49",
    50: "50-55",
    56: "56+",
}

OCUPACOES = {
    0: "outra/não informado",
    1: "docente/pesquisador",
    2: "artista",
    3: "administrativo",
    4: "estudante universitário",
    5: "atendimento ao cliente",
    6: "área da saúde",
    7: "executivo/gerência",
    8: "agricultor",
    9: "do lar",
    10: "estudante (ensino básico/médio)",
    11: "advogado",
    12: "programador",
    13: "aposentado",
    14: "vendas/marketing",
    15: "cientista",
    16: "autônomo",
    17: "técnico/engenheiro",
    18: "artesão/operário",
    19: "desempregado",
    20: "escritor",
}


def numero(valor, casas=0):
    """Formata no padrão brasileiro: ponto no milhar, vírgula no decimal."""
    return f"{valor:,.{casas}f}".replace(",", "#").replace(".", ",").replace("#", ".")


def pct(valor, casas=1):
    return f"{numero(valor * 100, casas)}%"


def ano_texto(valor):
    """Ano não leva separador de milhar."""
    return "sem ano" if pd.isna(valor) else f"{int(round(valor))}"


def secao(texto):
    print("\n" + "=" * LARGURA)
    print(texto.upper())
    print("=" * LARGURA)


def cabecalho(texto):
    print(f"\n{texto}")
    print("-" * len(texto))


def paragrafo(texto):
    print(textwrap.fill(" ".join(texto.split()), width=LARGURA))


def frase(texto):
    print(textwrap.fill(" ".join(texto.split()), width=LARGURA, subsequent_indent="   "))


def bloco(titulo, texto):
    """Um mini-título e um parágrafo indentado logo abaixo."""
    print(f"\n{titulo}")
    print(
        textwrap.fill(
            " ".join(texto.split()),
            width=LARGURA,
            initial_indent="  ",
            subsequent_indent="  ",
        )
    )


def ler_dat(arquivo, colunas):
    """Os .dat usam '::' como separador e vêm em latin-1, não UTF-8."""
    return pd.read_csv(
        os.path.join(BASE_DIR, arquivo),
        sep="::",
        engine="python",
        names=colunas,
        encoding="latin-1",
    )


def resumo(dados, coluna, valor="Rating"):
    """Quantas avaliações e qual a nota média de cada categoria."""
    return dados.groupby(coluna, observed=True)[valor].agg(n="count", media="mean")


def lista_participacao(serie, quantidade=3):
    """'Drama (17,3%), Comedy (16,1%), ...' — participação, ordem decrescente."""
    maiores = serie.sort_values(ascending=False).head(quantidade)
    return ", ".join(f"{nome} ({pct(valor, 1)})" for nome, valor in maiores.items())


def lista_medias(serie, quantidade=3, ascendente=False):
    """'Film-Noir (4,10), War (3,90), ...' — nota média, ordem escolhida."""
    ordenada = serie.sort_values(ascending=ascendente).head(quantidade)
    return ", ".join(f"{nome} ({numero(valor, 2)})" for nome, valor in ordenada.items())


def filmes_mais_avaliados(sub, quantidade=3):
    """Os filmes com mais notas dentro de um grupo, com a média que o grupo deu."""
    contagem = sub["MovieID"].value_counts().head(quantidade)
    medias = sub.groupby("MovieID")["Rating"].mean()
    return ", ".join(
        f"{titulos[mid]} ({numero(qtd)} notas, média {numero(medias[mid], 2)})"
        for mid, qtd in contagem.items()
    )


# ---------------------------------------------------------------------------
# Carga e preparo
# ---------------------------------------------------------------------------

ratings = ler_dat("ratings.dat", ["UserID", "MovieID", "Rating", "Timestamp"])
users = ler_dat("users.dat", ["UserID", "Gender", "Age", "Occupation", "ZipCode"])
movies = ler_dat("movies.dat", ["MovieID", "Title", "Genres"])

# Guardo os códigos originais antes de traduzir, caso precise deles depois.
users["Age_Code"] = users["Age"]
users["Occupation_Code"] = users["Occupation"]
users["Age"] = pd.Categorical(
    users["Age"].map(FAIXAS_ETARIAS), list(FAIXAS_ETARIAS.values()), ordered=True
)
users["Occupation"] = users["Occupation"].map(OCUPACOES)
users["Sexo"] = users["Gender"].map({"M": "Masculino", "F": "Feminino"})

ratings["Datetime"] = pd.to_datetime(ratings["Timestamp"], unit="s")
ratings["Year"] = ratings["Datetime"].dt.year

# O ano de lançamento está no fim do título, entre parênteses: "Toy Story (1995)".
extraido = movies["Title"].str.extract(r"^(?P<Nome>.*)\((?P<Ano>\d{4})\)\s*$")
movies["Nome"] = extraido["Nome"].str.strip()
movies["Ano"] = pd.to_numeric(extraido["Ano"])
movies["Decada"] = (movies["Ano"] // 10 * 10).astype("Int64")
movies["QtdGeneros"] = movies["Genres"].str.count(r"\|") + 1

titulos = movies.set_index("MovieID")["Title"]

df = ratings.merge(users, on="UserID", how="left").merge(
    movies[["MovieID", "Title", "Nome", "Genres", "Ano", "Decada", "QtdGeneros"]],
    on="MovieID",
    how="left",
)

# Um filme pode ter vários gêneros separados por "|". Exploto o catálogo (3.883
# linhas) e só depois cruzo com as avaliações — é bem mais rápido que explodir
# um milhão de linhas.
catalogo_genero = movies.assign(Genero=movies["Genres"].str.split("|")).explode("Genero")
generos = df[["UserID", "MovieID", "Rating", "Sexo", "Age", "Occupation", "Ano"]].merge(
    catalogo_genero[["MovieID", "Genero"]], on="MovieID", how="inner"
)
generos["Genero"] = generos["Genero"].astype("category")

por_usuario = ratings.groupby("UserID").size()
por_filme = ratings.groupby("MovieID").size()

filmes = df.groupby("MovieID")["Rating"].agg(n="count", media="mean")
filmes = filmes.join(movies.set_index("MovieID")[["Title", "Genres", "Ano", "Decada"]])
filmes_genero = catalogo_genero[["MovieID", "Genero"]].merge(
    filmes.reset_index(), on="MovieID", how="inner"
)

lista_generos = sorted(catalogo_genero["Genero"].unique())

# Participação de cada gênero nas avaliações do grupo e nota média que o grupo
# dá a cada gênero. As duas leituras são contagem e média, nada além disso.
participacao_genero_sexo = pd.crosstab(generos["Sexo"], generos["Genero"], normalize="index")
participacao_genero_idade = pd.crosstab(generos["Age"], generos["Genero"], normalize="index")
participacao_genero_ocupacao = pd.crosstab(
    generos["Occupation"], generos["Genero"], normalize="index"
)
media_genero_sexo = generos.pivot_table(
    index="Sexo", columns="Genero", values="Rating", aggfunc="mean", observed=True
)
media_genero_idade = generos.pivot_table(
    index="Age", columns="Genero", values="Rating", aggfunc="mean", observed=True
)
media_genero_ocupacao = generos.pivot_table(
    index="Occupation", columns="Genero", values="Rating", aggfunc="mean", observed=True
)


# ---------------------------------------------------------------------------
# Base e consistência
# ---------------------------------------------------------------------------

secao("Base e consistência")

paragrafo(
    f"Foram lidas {numero(len(ratings))} linhas de ratings.dat, {numero(len(users))} de "
    f"users.dat e {numero(len(movies))} de movies.dat."
)
print()
paragrafo(
    f"Há {ratings.loc[~ratings['MovieID'].isin(movies['MovieID']), 'MovieID'].nunique()} "
    f"MovieIDs em ratings.dat sem correspondência em movies.dat. Os três arquivos somam "
    f"{ratings.isna().sum().sum() + users.isna().sum().sum() + movies.isna().sum().sum()} "
    f"valores nulos. Em ratings.dat existem {ratings.duplicated().sum()} linhas totalmente "
    f"duplicadas, {ratings.duplicated(['UserID', 'MovieID']).sum()} pares de usuário e filme "
    f"repetidos e {(~ratings['Rating'].between(1, 5)).sum()} notas fora do intervalo de 1 a 5. "
    f"O ano de lançamento foi extraído do título em {numero(movies['Ano'].notna().sum())} dos "
    f"{numero(len(movies))} filmes ({numero(movies['Ano'].isna().sum())} sem ano) e "
    f"{numero(movies['Title'].duplicated().sum())} títulos aparecem repetidos no catálogo."
)


# ---------------------------------------------------------------------------
# Panorama geral
# ---------------------------------------------------------------------------

secao("Panorama geral")

paragrafo(
    f"A base reúne {numero(len(ratings))} avaliações feitas por {numero(len(por_usuario))} "
    f"usuários sobre {numero(len(por_filme))} filmes distintos, de um catálogo de "
    f"{numero(len(movies))} títulos — ou seja, {numero(len(movies) - len(por_filme))} filmes "
    f"nunca receberam nota. A nota média geral é {numero(ratings['Rating'].mean(), 3)} e as "
    f"avaliações foram registradas entre {ratings['Datetime'].min():%d/%m/%Y} e "
    f"{ratings['Datetime'].max():%d/%m/%Y}, preenchendo "
    f"{pct(len(ratings) / (len(por_usuario) * len(por_filme)), 2)} da matriz usuário por filme."
)
print()
paragrafo(
    f"Cada usuário avaliou de {numero(por_usuario.min())} a {numero(por_usuario.max())} filmes, "
    f"{numero(por_usuario.mean(), 1)} em média. Do lado dos filmes a diferença é muito maior: de "
    f"{numero(por_filme.min())} a {numero(por_filme.max())} avaliações, "
    f"{numero(por_filme.mean(), 1)} em média. "
    f"{pct(por_filme.le(10).mean(), 1)} dos filmes avaliados têm no máximo 10 notas, e "
    f"{pct(por_filme.ge(1000).mean(), 1)} passam de mil."
)

cabecalho("Quantas vezes cada nota foi dada")
distribuicao = ratings["Rating"].value_counts().sort_index()
for nota, quantidade in distribuicao.items():
    frase(
        f"A nota {nota} foi dada {numero(quantidade)} vezes, "
        f"{pct(quantidade / len(ratings), 2)} do total."
    )
print()
paragrafo(
    f"A nota mais frequente é {distribuicao.idxmax()}, com {numero(distribuicao.max())} "
    f"ocorrências, e a menos frequente é {distribuicao.idxmin()}, com "
    f"{numero(distribuicao.min())}. É essa contagem que sustenta a média geral de "
    f"{numero(ratings['Rating'].mean(), 3)} usada como referência no resto do relatório."
)


# ---------------------------------------------------------------------------
# Filmes
# ---------------------------------------------------------------------------

secao("Filmes")


def descrever_filmes(tabela):
    for posicao, (_, linha) in enumerate(tabela.iterrows(), 1):
        frase(
            f"{posicao}º — {linha['Title']}: {numero(linha['n'])} avaliações, nota média "
            f"{numero(linha['media'], 2)}. Gêneros: {linha['Genres'].replace('|', ', ')}."
        )


com_volume = filmes[filmes["n"] >= MIN_FILME]

cabecalho("Os 10 mais avaliados")
descrever_filmes(filmes.sort_values("n", ascending=False).head(10))

cabecalho(f"As 10 melhores notas (mínimo de {MIN_FILME} avaliações)")
descrever_filmes(com_volume.sort_values("media", ascending=False).head(10))

cabecalho(f"As 5 piores notas (mínimo de {MIN_FILME} avaliações)")
descrever_filmes(com_volume.sort_values("media").head(5))


# ---------------------------------------------------------------------------
# Gêneros
# ---------------------------------------------------------------------------

secao("Gêneros")

filmes_por_genero = catalogo_genero["Genero"].value_counts()
avaliacoes_por_genero = generos["Genero"].value_counts()
share_genero = avaliacoes_por_genero / avaliacoes_por_genero.sum()
resumo_genero = resumo(generos, "Genero")
usuarios_por_genero = generos.groupby("Genero", observed=True)["UserID"].nunique()
contagem_sexo_genero = pd.crosstab(generos["Sexo"], generos["Genero"])
ano_medio_genero = generos.groupby("Genero", observed=True)["Ano"].mean()
antigos_genero = (
    generos.assign(Antigo=generos["Ano"].lt(1980))
    .groupby("Genero", observed=True)["Antigo"]
    .mean()
)
combinacoes = movies["Genres"].value_counts()
rotulos_unicos = combinacoes[~combinacoes.index.str.contains(r"\|")]
rotulos_multiplos = combinacoes[combinacoes.index.str.contains(r"\|")]

paragrafo(
    f"O catálogo usa {len(lista_generos)} gêneros e cada filme carrega em média "
    f"{numero(movies['QtdGeneros'].mean(), 2)} deles (de 1 a {movies['QtdGeneros'].max()}); "
    f"{pct(movies['QtdGeneros'].eq(1).mean(), 1)} dos títulos têm um gênero só. Por isso uma "
    f"mesma avaliação é contada em mais de um gênero: as {numero(len(ratings))} avaliações viram "
    f"{numero(len(generos))} pares filme-gênero, e os percentuais abaixo somam mais de 100%. "
    f"Para não confundir, uso duas leituras: a participação no total de "
    f"{numero(len(generos))} pares e o alcance, que é a fatia dos {numero(len(por_usuario))} "
    f"usuários que avaliou pelo menos um filme do gênero."
)
print()
unicos = ", ".join(
    f"{nome} ({numero(qtd)})" for nome, qtd in rotulos_unicos.head(5).items()
)
multiplos = ", ".join(
    f"{nome.replace('|', ' + ')} ({numero(qtd)})" for nome, qtd in rotulos_multiplos.head(5).items()
)
paragrafo(
    f"Entre os {numero(movies['QtdGeneros'].eq(1).sum())} filmes de gênero único, os rótulos "
    f"mais frequentes são {unicos}. Entre os {numero(movies['QtdGeneros'].gt(1).sum())} filmes "
    f"com mais de um gênero, as combinações mais comuns são {multiplos}, e existem "
    f"{numero(len(rotulos_multiplos))} combinações distintas no catálogo."
)

cabecalho("Um a um")
for genero in avaliacoes_por_genero.index:
    linha = resumo_genero.loc[genero]
    sub = filmes_genero[filmes_genero["Genero"] == genero]
    com_corte = sub[sub["n"] >= MIN_GENERO]
    mais_avaliado = sub.loc[sub["n"].idxmax()]
    melhor = com_corte.loc[com_corte["media"].idxmax()]
    pior = com_corte.loc[com_corte["media"].idxmin()]
    participacao_f = (
        contagem_sexo_genero.loc["Feminino", genero] / contagem_sexo_genero[genero].sum()
    )
    faixa_top = participacao_genero_idade[genero].idxmax()
    faixa_baixo = participacao_genero_idade[genero].idxmin()

    bloco(
        genero,
        f"Catálogo: {numero(filmes_por_genero[genero])} filmes "
        f"({pct(filmes_por_genero[genero] / len(movies), 1)} dos {numero(len(movies))} títulos), "
        f"dos quais {numero(len(sub))} receberam nota. "
        f"Volume: {numero(int(linha['n']))} avaliações, {pct(share_genero[genero], 2)} dos pares "
        f"filme-gênero, vindas de {numero(usuarios_por_genero[genero])} usuários distintos — "
        f"alcance de {pct(usuarios_por_genero[genero] / len(por_usuario), 1)} da base. "
        f"Nota média {numero(linha['media'], 3)}. "
        f"Destaques: o mais visto é {mais_avaliado['Title']} ({numero(mais_avaliado['n'])} notas, "
        f"média {numero(mais_avaliado['media'], 2)}); com pelo menos {MIN_GENERO} avaliações, a "
        f"melhor nota é de {melhor['Title']} ({numero(melhor['media'], 2)} em "
        f"{numero(melhor['n'])} notas) e a pior de {pior['Title']} ({numero(pior['media'], 2)} em "
        f"{numero(pior['n'])} notas). "
        f"Público: as mulheres respondem por {pct(participacao_f, 1)} das avaliações do gênero e "
        f"dão média {numero(media_genero_sexo.loc['Feminino', genero], 3)}, contra "
        f"{numero(media_genero_sexo.loc['Masculino', genero], 3)} dos homens; o gênero pesa "
        f"{pct(participacao_genero_idade.loc[faixa_top, genero], 1)} das avaliações da faixa "
        f"{faixa_top}, sua maior presença, e {pct(participacao_genero_idade.loc[faixa_baixo, genero], 1)} "
        f"na faixa {faixa_baixo}, a menor. "
        f"Repertório: o ano médio de lançamento dos filmes avaliados no gênero é "
        f"{ano_texto(ano_medio_genero[genero])} e {pct(antigos_genero[genero], 1)} das avaliações "
        f"são de filmes anteriores a 1980.",
    )

cabecalho("Comparando os gêneros")
por_media = resumo_genero.sort_values("media", ascending=False)
top_media = ", ".join(
    f"{nome} ({numero(linha['media'], 2)} em {numero(int(linha['n']))} avaliações)"
    for nome, linha in por_media.head(3).iterrows()
)
fundo_media = ", ".join(
    f"{nome} ({numero(linha['media'], 2)} em {numero(int(linha['n']))} avaliações)"
    for nome, linha in por_media.tail(3).iterrows()
)
paragrafo(
    f"As melhores médias são de {top_media} e as piores de {fundo_media} — uma amplitude de "
    f"{numero(por_media['media'].max() - por_media['media'].min(), 2)} ponto entre o primeiro e o "
    f"último gênero."
)
print()
maior_alcance = usuarios_por_genero.idxmax()
menor_alcance = usuarios_por_genero.idxmin()
paragrafo(
    f"Volume e nota não andam juntos. {avaliacoes_por_genero.index[0]} é o gênero mais avaliado "
    f"({numero(avaliacoes_por_genero.iloc[0])} avaliações) e fica em "
    f"{list(por_media.index).index(avaliacoes_por_genero.index[0]) + 1}º na média; já "
    f"{por_media.index[0]}, dono da melhor média, tem só "
    f"{numero(int(por_media.iloc[0]['n']))} avaliações. Em alcance, {maior_alcance} chega a "
    f"{pct(usuarios_por_genero.max() / len(por_usuario), 1)} dos usuários e {menor_alcance} a "
    f"apenas {pct(usuarios_por_genero.min() / len(por_usuario), 1)}."
)


# ---------------------------------------------------------------------------
# Década de lançamento
# ---------------------------------------------------------------------------

secao("Década de lançamento")

com_ano = df[df["Decada"].notna()].copy()
com_ano["Decada"] = com_ano["Decada"].astype(int)
resumo_decada = resumo(com_ano, "Decada")
filmes_decada = movies.groupby("Decada", observed=True).size()

paragrafo(
    f"Os filmes do catálogo vão de {int(movies['Ano'].min())} a {int(movies['Ano'].max())}, com "
    f"ano médio de lançamento {ano_texto(movies['Ano'].mean())}. "
    f"{pct(movies['Ano'].ge(1990).mean(), 1)} dos títulos são de 1990 em diante, e eles "
    f"concentram {pct(com_ano['Ano'].ge(1990).mean(), 1)} das avaliações — a base é fortemente "
    f"puxada pelos lançamentos recentes na época da coleta."
)
print()
for decada, linha in resumo_decada.iterrows():
    frase(
        f"Anos {decada}: {numero(int(filmes_decada.get(decada, 0)))} filmes no catálogo e "
        f"{numero(int(linha['n']))} avaliações ({pct(linha['n'] / len(com_ano), 2)} do total), "
        f"com nota média {numero(linha['media'], 3)}."
    )
print()
paragrafo(
    f"A leitura é consistente: quanto mais antigo o filme que chega a ser avaliado, melhor a "
    f"nota. A melhor década é a de {resumo_decada['media'].idxmax()} "
    f"({numero(resumo_decada['media'].max(), 3)}) e a pior a de "
    f"{resumo_decada['media'].idxmin()} ({numero(resumo_decada['media'].min(), 3)}), "
    f"{numero(resumo_decada['media'].max() - resumo_decada['media'].min(), 3)} ponto de "
    f"diferença. Isso não diz que o cinema piorou: dos filmes antigos, só os que sobreviveram ao "
    f"tempo continuam sendo assistidos e avaliados, enquanto o catálogo recente entra inteiro, "
    f"com bons e ruins."
)


# ---------------------------------------------------------------------------
# Perfil dos usuários
# ---------------------------------------------------------------------------

secao("Perfil dos usuários")

contagem_sexo = users["Sexo"].value_counts()
paragrafo(
    f"Dos {numero(len(users))} usuários, {numero(contagem_sexo['Masculino'])} são homens "
    f"({pct(contagem_sexo['Masculino'] / len(users), 2)}) e "
    f"{numero(contagem_sexo['Feminino'])} são mulheres "
    f"({pct(contagem_sexo['Feminino'] / len(users), 2)})."
)
print()
avaliacoes_faixa = df["Age"].value_counts()
for faixa, quantidade in users["Age"].value_counts().sort_index().items():
    total_faixa = int(avaliacoes_faixa.get(faixa, 0))
    frase(
        f"A faixa {faixa} tem {numero(quantidade)} usuários "
        f"({pct(quantidade / len(users), 2)} da base) e responde por "
        f"{numero(total_faixa)} avaliações ({pct(total_faixa / len(df), 2)} do total)."
    )


# ---------------------------------------------------------------------------
# Faixa etária
# ---------------------------------------------------------------------------

secao("Faixa etária, a fundo")

resumo_idade = resumo(df, "Age")
atividade = por_usuario.rename("Avaliacoes").reset_index().merge(
    users[["UserID", "Age", "Sexo", "Occupation"]], on="UserID"
)

for faixa in resumo_idade.index:
    linha = resumo_idade.loc[faixa]
    usuarios_faixa = atividade[atividade["Age"] == faixa]
    sub = df[df["Age"] == faixa]
    mulheres = usuarios_faixa["Sexo"].eq("Feminino").mean()
    ocupacao_top = usuarios_faixa["Occupation"].value_counts().head(1)

    bloco(
        f"{faixa}",
        f"Tamanho: {numero(len(usuarios_faixa))} usuários "
        f"({pct(len(usuarios_faixa) / len(users), 1)} da base), sendo {pct(mulheres, 1)} mulheres, "
        f"e a ocupação mais comum é {ocupacao_top.index[0]} "
        f"({numero(int(ocupacao_top.iloc[0]))} pessoas). "
        f"Atividade: {numero(int(linha['n']))} avaliações no total "
        f"({pct(linha['n'] / len(df), 2)} da base), o que dá "
        f"{numero(usuarios_faixa['Avaliacoes'].mean(), 1)} por usuário na média, indo de "
        f"{numero(usuarios_faixa['Avaliacoes'].min())} a "
        f"{numero(usuarios_faixa['Avaliacoes'].max())}. "
        f"Nota média {numero(linha['media'], 3)}. "
        f"Gêneros que mais aparecem nas avaliações da faixa: "
        f"{lista_participacao(participacao_genero_idade.loc[faixa])}. "
        f"Os que a faixa melhor avalia são "
        f"{lista_medias(media_genero_idade.loc[faixa])} e os piores, "
        f"{lista_medias(media_genero_idade.loc[faixa], ascendente=True)}. "
        f"Repertório: {pct(sub['Ano'].ge(1990).mean(), 1)} das avaliações da faixa são de filmes "
        f"lançados de 1990 em diante e {pct(sub['Ano'].lt(1980).mean(), 1)} de filmes anteriores "
        f"a 1980, com ano médio de lançamento {ano_texto(sub['Ano'].mean())}. "
        f"Os filmes mais avaliados pela faixa são {filmes_mais_avaliados(sub)}.",
    )

cabecalho("O que muda de fato entre as faixas")
media_faixa = atividade.groupby("Age", observed=True)["Avaliacoes"].mean()
paragrafo(
    f"A nota média vai de {numero(resumo_idade['media'].min(), 3)} "
    f"({resumo_idade['media'].idxmin()}) a {numero(resumo_idade['media'].max(), 3)} "
    f"({resumo_idade['media'].idxmax()}), uma amplitude de "
    f"{numero(resumo_idade['media'].max() - resumo_idade['media'].min(), 3)} ponto — pequena "
    f"perto da diferença de comportamento. O contraste real está no volume e no repertório: a "
    f"faixa {media_faixa.idxmax()} avalia {numero(media_faixa.max(), 1)} filmes por usuário na "
    f"média e a faixa {media_faixa.idxmin()} apenas {numero(media_faixa.min(), 1)}, e a "
    f"preferência por filmes anteriores a 1980 cresce de "
    f"{pct(df[df['Age'] == 'Menor de 18']['Ano'].lt(1980).mean(), 1)} entre os menores de 18 para "
    f"{pct(df[df['Age'] == '56+']['Ano'].lt(1980).mean(), 1)} na faixa 56+."
)


# ---------------------------------------------------------------------------
# Sexo
# ---------------------------------------------------------------------------

secao("Sexo, a fundo")

resumo_sexo = resumo(df, "Sexo")
for sexo in ["Feminino", "Masculino"]:
    linha = resumo_sexo.loc[sexo]
    usuarios_sexo = atividade[atividade["Sexo"] == sexo]
    sub = df[df["Sexo"] == sexo]

    bloco(
        sexo,
        f"Tamanho: {numero(len(usuarios_sexo))} usuários "
        f"({pct(len(usuarios_sexo) / len(users), 1)} da base) responsáveis por "
        f"{numero(int(linha['n']))} avaliações ({pct(linha['n'] / len(df), 1)} do total), "
        f"{numero(usuarios_sexo['Avaliacoes'].mean(), 1)} por pessoa na média. "
        f"Nota média {numero(linha['media'], 3)}. "
        f"Gêneros que mais aparecem nas avaliações: "
        f"{lista_participacao(participacao_genero_sexo.loc[sexo])}. "
        f"Os mais bem avaliados são {lista_medias(media_genero_sexo.loc[sexo])} e os piores, "
        f"{lista_medias(media_genero_sexo.loc[sexo], ascendente=True)}. "
        f"Repertório: {pct(sub['Ano'].lt(1980).mean(), 1)} das avaliações são de filmes "
        f"anteriores a 1980, com ano médio de lançamento {ano_texto(sub['Ano'].mean())}. "
        f"Os filmes mais avaliados são {filmes_mais_avaliados(sub)}.",
    )

print()
diferenca_media = resumo_sexo.loc["Feminino", "media"] - resumo_sexo.loc["Masculino", "media"]
paragrafo(
    f"A diferença de nota média entre mulheres e homens é de "
    f"{numero(abs(diferenca_media), 3)} ponto "
    f"({'a favor das mulheres' if diferenca_media > 0 else 'a favor dos homens'}) — pequena "
    f"diante do que separa os dois na escolha do que assistir."
)
print()
distancia_genero = (
    participacao_genero_sexo.loc["Feminino"] - participacao_genero_sexo.loc["Masculino"]
).sort_values(ascending=False)
mais_fem = ", ".join(
    f"{nome} ({pct(participacao_genero_sexo.loc['Feminino', nome], 1)} das avaliações delas "
    f"contra {pct(participacao_genero_sexo.loc['Masculino', nome], 1)} das deles)"
    for nome in distancia_genero.head(3).index
)
mais_masc = ", ".join(
    f"{nome} ({pct(participacao_genero_sexo.loc['Masculino', nome], 1)} contra "
    f"{pct(participacao_genero_sexo.loc['Feminino', nome], 1)})"
    for nome in distancia_genero.tail(3).index[::-1]
)
paragrafo(
    f"Os gêneros com maior peso nas avaliações femininas do que nas masculinas são {mais_fem}. "
    f"Do outro lado, os que pesam mais entre os homens são {mais_masc}."
)

cabecalho("Nota média por faixa etária e sexo")
media_cruzada = df.pivot_table(index="Age", columns="Sexo", values="Rating",
                               aggfunc="mean", observed=True)
volume_cruzado = df.pivot_table(index="Age", columns="Sexo", values="Rating",
                                aggfunc="count", observed=True)
for faixa in media_cruzada.index:
    frase(
        f"Na faixa {faixa}, as mulheres deram média "
        f"{numero(media_cruzada.loc[faixa, 'Feminino'], 3)} em "
        f"{numero(volume_cruzado.loc[faixa, 'Feminino'])} avaliações, contra "
        f"{numero(media_cruzada.loc[faixa, 'Masculino'], 3)} dos homens em "
        f"{numero(volume_cruzado.loc[faixa, 'Masculino'])} avaliações — diferença de "
        f"{numero(media_cruzada.loc[faixa, 'Feminino'] - media_cruzada.loc[faixa, 'Masculino'], 3)} "
        f"ponto."
    )


# ---------------------------------------------------------------------------
# Ocupação
# ---------------------------------------------------------------------------

secao("Ocupação, a fundo")

resumo_ocupacao = resumo(df, "Occupation").sort_values("n", ascending=False)
usuarios_ocupacao = users["Occupation"].value_counts()

paragrafo(
    f"São {len(OCUPACOES)} ocupações declaradas. A maior é "
    f"{usuarios_ocupacao.index[0]}, com {numero(usuarios_ocupacao.iloc[0])} usuários "
    f"({pct(usuarios_ocupacao.iloc[0] / len(users), 1)} da base), e a menor é "
    f"{usuarios_ocupacao.index[-1]}, com {numero(usuarios_ocupacao.iloc[-1])} "
    f"({pct(usuarios_ocupacao.iloc[-1] / len(users), 1)}). Grupos pequenos como esse pesam pouco "
    f"no total, e por isso as contagens vêm junto de cada média — abaixo elas estão ordenadas "
    f"por volume de avaliações."
)

for ocupacao, linha in resumo_ocupacao.iterrows():
    usuarios_grupo = atividade[atividade["Occupation"] == ocupacao]
    sub = df[df["Occupation"] == ocupacao]
    faixa_top = usuarios_grupo["Age"].value_counts().head(1)
    bloco(
        ocupacao.capitalize(),
        f"{numero(len(usuarios_grupo))} usuários ({pct(len(usuarios_grupo) / len(users), 1)} da "
        f"base), {pct(usuarios_grupo['Sexo'].eq('Feminino').mean(), 1)} deles mulheres, faixa "
        f"etária predominante {faixa_top.index[0]} "
        f"({pct(faixa_top.iloc[0] / len(usuarios_grupo), 1)} do grupo). "
        f"Somam {numero(int(linha['n']))} avaliações ({pct(linha['n'] / len(df), 2)} do total), "
        f"{numero(usuarios_grupo['Avaliacoes'].mean(), 1)} por usuário na média. "
        f"Nota média {numero(linha['media'], 3)}. "
        f"Gêneros que mais aparecem nas avaliações do grupo: "
        f"{lista_participacao(participacao_genero_ocupacao.loc[ocupacao], quantidade=2)}. "
        f"Os mais bem avaliados são "
        f"{lista_medias(media_genero_ocupacao.loc[ocupacao], quantidade=2)} e os piores, "
        f"{lista_medias(media_genero_ocupacao.loc[ocupacao], quantidade=2, ascendente=True)}. "
        f"{pct(sub['Ano'].lt(1980).mean(), 1)} das avaliações do grupo são de filmes anteriores a "
        f"1980.",
    )

print()
por_media_ocupacao = resumo_ocupacao.sort_values("media", ascending=False)
paragrafo(
    f"Entre as {len(por_media_ocupacao)} ocupações, a maior nota média é de "
    f"{por_media_ocupacao.index[0]} ({numero(por_media_ocupacao.iloc[0]['media'], 3)} em "
    f"{numero(int(por_media_ocupacao.iloc[0]['n']))} avaliações) e a menor de "
    f"{por_media_ocupacao.index[-1]} ({numero(por_media_ocupacao.iloc[-1]['media'], 3)} em "
    f"{numero(int(por_media_ocupacao.iloc[-1]['n']))}), amplitude de "
    f"{numero(por_media_ocupacao['media'].max() - por_media_ocupacao['media'].min(), 3)} ponto. "
    f"O grupo mais ativo é {resumo_ocupacao.index[0]}, com "
    f"{pct(resumo_ocupacao.iloc[0]['n'] / len(df), 1)} de todas as avaliações."
)


# ---------------------------------------------------------------------------
# Tempo
# ---------------------------------------------------------------------------

secao("Avaliações ao longo do tempo")

resumo_ano = resumo(ratings, "Year")
usuarios_ano = ratings.groupby("Year")["UserID"].nunique()
for ano, linha in resumo_ano.iterrows():
    frase(
        f"Em {ano} foram registradas {numero(int(linha['n']))} avaliações "
        f"({pct(linha['n'] / len(ratings), 2)} do total) por {numero(usuarios_ano[ano])} usuários "
        f"distintos, com nota média {numero(linha['media'], 3)}."
    )
print()
por_mes = ratings.groupby(ratings["Datetime"].dt.to_period("M")).size()
maiores_meses = por_mes.sort_values(ascending=False).head(3)
lista_meses = ", ".join(
    f"{mes} ({numero(qtd)} avaliações)" for mes, qtd in maiores_meses.items()
)
paragrafo(
    f"A coleta durou {len(por_mes)} meses, mas foi tudo menos uniforme: os três meses de maior "
    f"volume — {lista_meses} — concentram {pct(maiores_meses.sum() / len(ratings), 1)} de toda a "
    f"base, e o mais fraco, {por_mes.idxmin()}, teve {numero(por_mes.min())}. São três meses de "
    f"2000, e é essa concentração que faz o ano responder por "
    f"{pct(resumo_ano.loc[2000, 'n'] / len(ratings), 1)} das avaliações, e não uma atividade "
    f"constante ao longo dos três anos. A queda de "
    f"{numero(resumo_ano.loc[2000, 'media'] - resumo_ano.loc[2002, 'media'], 3)} ponto na média "
    f"entre 2000 e 2002 vem junto com a troca de quem está avaliando: de "
    f"{numero(usuarios_ano[2000])} usuários ativos em 2000 para {numero(usuarios_ano[2002])} em "
    f"2002, ou seja, o que sobra no fim é um grupo pequeno de usuários mais assíduos, não a base "
    f"inteira mudando de opinião."
)


# ---------------------------------------------------------------------------
# Nota metodológica
# ---------------------------------------------------------------------------

secao("Nota metodológica")

paragrafo(
    "A média é a única medida de nota usada neste relatório. Todo o resto é contagem e "
    "participação: quantos filmes, quantas avaliações, quantos usuários distintos e que fatia do "
    "total cada categoria representa. Sempre que uma média aparece, o número de avaliações que a "
    "sustenta vem junto — é o que permite separar um resultado de 300 mil notas de outro de 50."
)
print()
paragrafo(
    "Ficaram de fora, por não fazerem sentido para uma nota ordinal de 1 a 5 medida sobre a base "
    "completa:"
)
print()
frase(
    "Coeficiente de variação — só faz sentido em escala com zero absoluto, como renda ou "
    "contagem. A nota vai de 1 a 5 e o zero é arbitrário, então dividir o desvio padrão pela "
    "média não produz um número interpretável."
)
frase(
    "Intervalo de confiança da média — a base é o conjunto completo das avaliações do MovieLens, "
    "não uma amostra aleatória de uma população maior. Com centenas de milhares de notas por "
    "grupo, o intervalo fica em torno de ±0,003 ponto: precisão falsa que não muda nenhuma "
    "conclusão."
)
frase(
    "Teste de hipótese (Kruskal-Wallis, qui-quadrado e afins) — com um milhão de observações, "
    "qualquer diferença, mesmo de 0,01 ponto, sai com p praticamente zero. O teste confirmaria "
    "apenas que a base é grande, não que a diferença importa."
)
frase(
    "Mediana e quartis das notas — em escala de cinco pontos a mediana é 4 em quase todo grupo e "
    "o intervalo interquartil é 3 a 4 em praticamente todos, então não separam categoria nenhuma."
)
print()
paragrafo(
    "Também não entram desvio padrão, tamanho de efeito e índices compostos de afinidade ou "
    "concentração: onde os grupos precisam ser comparados, a comparação é feita direto entre as "
    "médias — a diferença em pontos entre a maior e a menor — e entre as participações "
    "percentuais, que são contagem pura."
)
