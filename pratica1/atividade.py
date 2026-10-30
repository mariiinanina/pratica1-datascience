
# ---
# PROJETO WEB SCRAPING - G1
# EXERCICIOS PRATICOS
# ----

import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
import random
import logging

from datetime import datetime
from urllib.parse import urljoin


# ---
# CONFIGURACAO INICIAL
# ---

inicio_execucao = time.time()

url = "https://g1.globo.com/"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8'
}

# Configuracao dos logs
logging.basicConfig(
    filename='log_g1.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

# Lista de noticias
noticias = []
categorias = []


# ---
# FUNCAO PARA REGISTRAR ERROS
# ---

def registrar_erro(mensagem):
    logging.error(mensagem)
    print("Erro:", mensagem)


def extrair_detalhes(link):

    detalhes = {
        "data_publicacao": None,
        "autor": None,
        "comentarios": None,
        "imagem": None
    }

    try:
        resposta = requests.get(
            link,
            headers=headers,
            timeout=15
        )

        resposta.raise_for_status()

        pagina = BeautifulSoup(resposta.text, 'html.parser')

        # Data de publicacao
        data = pagina.select_one(
            'meta[property="article:published_time"]'
        )

        if data:
            detalhes["data_publicacao"] = data.get('content')

        if not detalhes["data_publicacao"]:
            data = pagina.select_one('time[datetime]')

            if data:
                detalhes["data_publicacao"] = data.get('datetime')

        # Autor da noticia
        autor = pagina.select_one(
            'meta[name="author"], meta[property="article:author"]'
        )

        if autor:
            detalhes["autor"] = autor.get('content')

        if not detalhes["autor"]:
            autor = pagina.select_one(
                '[rel="author"], .content-publication-data__from'
            )

            if autor:
                detalhes["autor"] = autor.get_text(strip=True)

        # Numero de comentarios
        comentarios = pagina.select_one(
            '[data-comments-count], .comment-count, '
            '.comments-count, .quantity-comments'
        )

        if comentarios:
            valor = comentarios.get('data-comments-count')

            if valor is None:
                valor = comentarios.get_text(strip=True)

            detalhes["comentarios"] = valor

        # Imagem relacionada a noticia
        imagem = pagina.select_one(
            'meta[property="og:image"]'
        )

        if imagem:
            detalhes["imagem"] = imagem.get('content')

        if not detalhes["imagem"]:
            imagem = pagina.select_one('article img')

            if imagem:
                detalhes["imagem"] = (
                    imagem.get('src') or imagem.get('data-src')
                )

    except requests.exceptions.RequestException as e:
        registrar_erro(f"Erro ao acessar noticia {link}: {e}")

    except Exception as e:
        registrar_erro(f"Erro ao extrair detalhes: {e}")

    return detalhes


# ---
# CALCULO DE RELEVANCIA
# ---

def calcular_relevancia(noticia):

    # Palavras-chave que podem indicar relevancia
    palavras_chave = [
        'brasil',
        'economia',
        'politica',
        'saude',
        'educacao',
        'seguranca',
        'tecnologia',
        'urgente'
    ]

    titulo = noticia['titulo'].lower()

    pontuacao = 0

    for palavra in palavras_chave:
        if palavra in titulo:
            pontuacao += 1

    # Comentarios tambem podem ser considerados
    try:
        if noticia['comentarios'] is not None:
            pontuacao += int(noticia['comentarios']) / 10
    except (ValueError, TypeError):
        pass

    return pontuacao


# ---
# VALIDACAO DOS LINKS
# ---

def validar_link(link):

    resultado = {
        "status": "Invalido",
        "codigo_http": None,
        "redirecionado": False,
        "link_final": None
    }

    if not link or not link.startswith(('http://', 'https://')):
        return resultado

    try:
        resposta = requests.get(
            link,
            headers=headers,
            timeout=15,
            allow_redirects=True,
            stream=True
        )

        resultado["codigo_http"] = resposta.status_code
        resultado["link_final"] = resposta.url

        resultado["redirecionado"] = len(resposta.history) > 0

        if resposta.status_code < 400:
            resultado["status"] = "Ativo"
        else:
            resultado["status"] = "Quebrado"

        resposta.close()

    except requests.exceptions.RequestException as e:
        resultado["status"] = "Quebrado"
        registrar_erro(f"Link com problema {link}: {e}")

    return resultado


# =====================================================
# REQUISICAO HTTP
# =====================================================

try:

    print("Acessando o site G1...")

    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    print("Site acessado com sucesso!")

    logging.info("Requisicao HTTP realizada com sucesso.")


    # =================================================
    # EXTRAINDO CATEGORIAS
    # =================================================

    print("\nExtraindo categorias...")

    menu_items = soup.select('.menu-item')

    for item in menu_items:

        link = item.get('href')
        texto = item.get_text(strip=True)

        if link and texto:

            categorias.append({
                "nome": texto,
                "link": urljoin(url, link)
            })

    print("Categorias encontradas:", len(categorias))


    # =================================================
    # EXTRAINDO NOTICIAS
    # =================================================

    print("\nExtraindo noticias...")

    # Noticia principal
    destaques = soup.select('.bastian-page')

    if destaques:

        principal = destaques[0].select_one('.bastian-cover')

        if principal:

            titulo_element = principal.select_one(
                'h1, .content-head_title'
            )

            if titulo_element:

                link_element = principal.select_one('a')

                link = (
                    urljoin(url, link_element.get('href'))
                    if link_element and link_element.get('href')
                    else None
                )

                noticias.append({
                    "titulo": titulo_element.get_text(strip=True),
                    "link": link,
                    "tipo": "Destaque principal",
                    "categoria": "Não identificada",
                    "data_extracao": datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                })


    # Noticias regulares
    cards = soup.select(
        '.feed-post-body, .bstn-item, .bastian-feed-item'
    )

    for card in cards:

        try:

            titulo_element = card.select_one(
                '.feed-post-body-title, .bstn-hltitle'
            )

            if not titulo_element:
                continue

            titulo = titulo_element.get_text(strip=True)

            link_element = card.select_one('a')

            link = (
                urljoin(url, link_element.get('href'))
                if link_element and link_element.get('href')
                else None
            )

            if titulo:

                noticias.append({
                    "titulo": titulo,
                    "link": link,
                    "tipo": "Notícia regular",
                    "categoria": "Não identificada",
                    "data_extracao": datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                })

        except Exception as e:
            registrar_erro(f"Erro ao extrair card: {e}")


    # =================================================
    # EXTRAINDO VIDEOS
    # =================================================

    print("Extraindo videos...")

    videos = soup.select('.media-wrapper')

    for video in videos:

        try:

            titulo_element = video.select_one('title')

            if titulo_element:

                link_element = video.select_one('a')

                link = (
                    urljoin(url, link_element.get('href'))
                    if link_element and link_element.get('href')
                    else None
                )

                noticias.append({
                    "titulo": titulo_element.get_text(strip=True),
                    "link": link,
                    "tipo": "Vídeo",
                    "categoria": "Não identificada",
                    "data_extracao": datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                })

        except Exception as e:
            registrar_erro(f"Erro ao extrair video: {e}")


    # =================================================
    # REMOVENDO DUPLICATAS
    # =================================================

    noticias_unicas = []
    titulos_vistos = set()

    for noticia in noticias:

        titulo = noticia['titulo'].strip().lower()

        if titulo and titulo not in titulos_vistos:

            titulos_vistos.add(titulo)
            noticias_unicas.append(noticia)

    noticias = noticias_unicas

    print("Noticias unicas:", len(noticias))


    # =================================================
    # EXERCICIO 1 - COMPLETANDO DADOS DAS NOTICIAS
    # =================================================

    print("\nExtraindo informacoes adicionais...")

    # Limite para evitar muitas requisicoes seguidas
    for noticia in noticias[:20]:

        if noticia['link']:

            detalhes = extrair_detalhes(noticia['link'])

            noticia.update(detalhes)

            time.sleep(random.uniform(0.5, 1.5))

        else:

            noticia.update({
                "data_publicacao": None,
                "autor": None,
                "comentarios": None,
                "imagem": None
            })

    # Noticias restantes ficam com campos vazios
    for noticia in noticias[20:]:

        noticia.update({
            "data_publicacao": None,
            "autor": None,
            "comentarios": None,
            "imagem": None
        })


    # =================================================
    # EXERCICIO 2 - LOGS E CATEGORIAS
    # =================================================

    print("\nGerando relatorio de logs...")

    df = pd.DataFrame(noticias)

    if not df.empty:

        quantidade_categorias = df.groupby(
            'categoria'
        ).size()

        for categoria, quantidade in quantidade_categorias.items():

            logging.info(
                f"Categoria: {categoria} - Noticias: {quantidade}"
            )

            print(
                f"Categoria {categoria}: {quantidade} noticias"
            )


    # =================================================
    # EXERCICIO 3 - FILTRO POR DATA
    # =================================================

    print("\nFiltrando noticias por data...")

    if not df.empty:

        df['data_publicacao_convertida'] = pd.to_datetime(
            df['data_publicacao'],
            errors='coerce',
            utc=True
        )

        # Altere a data conforme desejar
        data_inicio = pd.Timestamp(
            '2026-01-01',
            tz='UTC'
        )

        noticias_filtradas = df[
            df['data_publicacao_convertida'] >= data_inicio
        ].copy()

        print(
            "Noticias a partir de 01/01/2026:",
            len(noticias_filtradas)
        )

        # Ordenar por relevancia
        df['relevancia'] = df.apply(
            lambda linha: calcular_relevancia(linha.to_dict()),
            axis=1
        )

        df_ordenado = df.sort_values(
            by='relevancia',
            ascending=False
        )

        print("\nNoticias ordenadas por relevancia:")

        for _, noticia in df_ordenado.head(10).iterrows():

            print(
                noticia['titulo'],
                "- Pontuacao:",
                noticia['relevancia']
            )

    else:

        noticias_filtradas = df.copy()
        df_ordenado = df.copy()


    # =================================================
    # EXERCICIO 4 - VALIDANDO OS LINKS
    # =================================================

    print("\nValidando links...")

    for noticia in noticias:

        resultado = validar_link(noticia['link'])

        noticia.update({
            "status_link": resultado["status"],
            "codigo_http": resultado["codigo_http"],
            "redirecionado": resultado["redirecionado"],
            "link_final": resultado["link_final"]
        })

        time.sleep(random.uniform(0.3, 0.8))


    # =================================================
    # SALVANDO OS ARQUIVOS CSV
    # =================================================

    df_final = pd.DataFrame(noticias)

    df_final.to_csv(
        'noticias_g1_expandido.csv',
        index=False,
        encoding='utf-8-sig'
    )

    pd.DataFrame(categorias).to_csv(
        'categorias_g1.csv',
        index=False,
        encoding='utf-8-sig'
    )

    # Salvar noticias filtradas
    noticias_filtradas.to_csv(
        'noticias_filtradas.csv',
        index=False,
        encoding='utf-8-sig'
    )

    # Salvar noticias ordenadas
    df_ordenado.to_csv(
        'noticias_por_relevancia.csv',
        index=False,
        encoding='utf-8-sig'
    )

    # Salvar links quebrados
    links_quebrados = df_final[
        df_final['status_link'] == 'Quebrado'
    ]

    links_quebrados.to_csv(
        'links_quebrados.csv',
        index=False,
        encoding='utf-8-sig'
    )


    # =================================================
    # TEMPO DE EXECUCAO
    # =================================================

    tempo_total = time.time() - inicio_execucao

    logging.info(
        f"Tempo total de execucao: {tempo_total:.2f} segundos"
    )

    logging.info(
        f"Total de noticias: {len(noticias)}"
    )

    logging.info(
        f"Total de categorias: {len(categorias)}"
    )

    print("\n===================================")
    print("PROCESSAMENTO FINALIZADO!")
    print("===================================")

    print("Noticias:", len(noticias))
    print("Categorias:", len(categorias))
    print("Links quebrados:", len(links_quebrados))
    print(f"Tempo de execucao: {tempo_total:.2f} segundos")

    print("\nArquivos gerados:")
    print("- noticias_g1_expandido.csv")
    print("- categorias_g1.csv")
    print("- noticias_filtradas.csv")
    print("- noticias_por_relevancia.csv")
    print("- links_quebrados.csv")
    print("- log_g1.txt")


except requests.exceptions.RequestException as e:

    registrar_erro(f"Erro na requisicao principal: {e}")

except Exception as e:

    registrar_erro(f"Erro geral no programa: {e}")
