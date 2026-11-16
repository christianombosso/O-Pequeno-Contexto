import math
import os
import random
import re
from xmlrpc.server import SimpleXMLRPCServer
import pdfplumber
import spacy
import stanza
import unidecode

caminho_livro = "recursos/livro.pdf"
primeirapg = 15
ultimapg = 206
freq_minima = 2

STOPWORDS = {
    "a", "o", "os", "as", "um", "uma", "uns", "umas",
    "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas",
    "para", "por", "pelo", "pela", "pelos", "pelas", "num", "numa",
    "com", "sem", "sobre", "entre", "ate", "apos", "durante",
    "e", "ou", "mas", "que", "se", "nao", "sim", "ja", "so",
    "eu", "tu", "ele", "ela", "nos", "vos", "eles", "elas", "voce", "voces",
    "me", "te", "lhe", "lhes", "meu", "minha", "meus", "minhas",
    "teu", "tua", "teus", "tuas", "seu", "sua", "seus", "suas",
    "nosso", "nossa", "nossos", "nossas", "este", "esta", "esses", "essas",
    "isto", "isso", "aquilo", "outro", "outra", "outros", "outras",
    "disse", "dizia", "respondeu", "perguntou", "exclamou", "pensou",
    "ser", "estar", "ter", "haver", "foi", "era", "eram", "sao", "vai",
    "vou", "vamos", "vem", "tinha", "tinham", "tem", "sendo", "sido",
    "muito", "pouco", "mais", "menos", "tao", "tanto", "bem", "mal", "ainda",
    "quando", "onde", "como", "porque", "pois", "entao", "assim", "tambem",
    "depois", "antes", "nunca", "sempre", "quase", "todo", "toda", "todos", "todas",
    "nada", "algo", "alguem", "ninguem", "cada", "tudo", "coisa", "coisas",
    "aqui", "ali", "la", "ai", "logo", "agora", "ah", "oh", "acrescentou", "hum",
    "dois", "duas", "tres", "quatro", "cinco", "seis", "sete", "onze", "doze",
    "quinze", "vinte", "trinta", "quarenta", "cinquenta", "quinhenta", "cem", "quatrocentos",
    "quatrocento", "quinhentos", "quinhento", "seiscentos", "seiscento",
    "setecentos", "setecento", "mil", "milhao", "milhoes", "bilhao", "bilhoes", "bril", "eis"
}

CORRECOES_LEMATIZACAO = {
    "ponhar": "por",
    "refizir": "refazer",
    "dormer": "dormir",
    "rer": "rir",
    "order": "ordem",
    "cater": "caber",
    "erguir": "erguer",
    "engolar": "engolir",
    "comprir": "cumprir",
    "raposo": "raposa"
}

nlp = stanza.Pipeline("pt", processors="tokenize,pos,lemma", verbose=False)

# função para extrair o texto do PDF entre o intervalo de páginas
def extrair_texto(caminho, pag_inicio, pag_fim):
    if not os.path.exists(caminho):
        raise FileNotFoundError(f"arquivo nao encontrado: {caminho}")

    paginas = []
    with pdfplumber.open(caminho) as pdf:
        for num_pagina in range(pag_inicio - 1, pag_fim):
            if num_pagina < len(pdf.pages):
                texto = pdf.pages[num_pagina].extract_text()
                if texto:
                    paginas.append(texto)
                    
    return "\n".join(paginas)

# função que recebe o texto do livro, extrai a forma base de cada palavra e remove acentos
def lematizar_e_tokenizar(texto):
    doc = nlp(texto)
    tokens = []
    for senteca in doc.sentences:
        for palavra in senteca.words:
            if palavra.lemma:
                lema = unidecode.unidecode(palavra.lemma.lower()) # remove acentos e converte para minúsculas
                
                if lema in CORRECOES_LEMATIZACAO:
                    lema = CORRECOES_LEMATIZACAO[lema] # corrige os lemas manualmente com base no nosso dicionário
                    
                if re.match(r'^[a-z]+$', lema): # filtra apenas palavras com letras (sem números ou símbolos)
                    tokens.append(lema)
    return tokens

# função pra lematizar e formatar os chutes do jogador 
def lematizar_palpite(palavra):
    doc = nlp(palavra)
    for senteca in doc.sentences:
        for word in senteca.words:
            if word.lemma:
                lema = unidecode.unidecode(word.lemma.lower())
                if lema in CORRECOES_LEMATIZACAO:
                    lema = CORRECOES_LEMATIZACAO[lema]
                return lema
    return unidecode.unidecode(palavra.lower().strip())

# função que remove as stopwords e palavras com menos de 3 letras
def remover_stopwords(tokens):
    return [
        t for t in tokens 
        if t not in STOPWORDS and len(t) > 2
    ]

# função para contar a frequência de cada palavra no texto
def contar_frequencia(tokens):
    contagem = {}
    for palavra in tokens:
        contagem[palavra] = contagem.get(palavra, 0) + 1
    return contagem

# função para montar o vocabulário final filtrando as palavras com frequência mínima
def montar_vocabulario(tokens):
    contagem = contar_frequencia(tokens)
    return {
        palavra: freq for palavra, freq in contagem.items()
        if freq >= freq_minima
    }

# função de pré-processamento do livro
def preprocessar_livro():
    texto_bruto = extrair_texto(caminho_livro, primeirapg, ultimapg)
    tokens_lematizados = lematizar_e_tokenizar(texto_bruto)
    tokens_filtrados = remover_stopwords(tokens_lematizados)
    vocabulario = montar_vocabulario(tokens_filtrados)
    return vocabulario

# função para carregar os vetores do modelo spaCy e mapear as palavras do vocabulário
def carregar_vetores(vocabulario, modelo_spacy="pt_core_news_md"):
    nlp_spacy = spacy.load(modelo_spacy)
    
    mapa_sem_acento = {} # mapeia palavras sem acento para seus vetores correspondentes
    for key in nlp_spacy.vocab.vectors: # percorre todas as palavras que possuem vetores no modelo spaCy
        termo_original = nlp_spacy.vocab.strings[key]
        if termo_original.isalpha(): # filtra apenas palavras com letras
            termo_limpo = unidecode.unidecode(termo_original.lower()) # remove acentos das palavras do modelo e converte para minúsculas
            if termo_limpo not in mapa_sem_acento: # se a palavra sem acento ainda não estiver no mapa, adiciona o vetor correspondente
                mapa_sem_acento[termo_limpo] = nlp_spacy.vocab[termo_original].vector.tolist()

    vetores = {}
    for palavra in vocabulario: # tenta encontrar o vetor correspondente para cada palavra do vocabulário
        if palavra in mapa_sem_acento:
            vetores[palavra] = mapa_sem_acento[palavra]
        else: # se a palavra não estiver no mapa, tenta buscar diretamente no vocabulário do modelo
            token_spacy = nlp_spacy.vocab[palavra]
            if token_spacy.has_vector:
                vetores[palavra] = token_spacy.vector.tolist()
            
    return vetores # retorna um dicionário com as palavras do vocabulário e seus vetores correspondentes

# função para calcular a similaridade por cosseno entre dois vetores
def calculo_similaridade(v1, v2): 
    produto_escalar = sum(a * b for a, b in zip(v1, v2))
    norma_v1 = math.sqrt(sum(a ** 2 for a in v1))
    norma_v2 = math.sqrt(sum(b ** 2 for b in v2))

    if norma_v1 == 0 or norma_v2 == 0:
        return 0.0

    return produto_escalar / (norma_v1 * norma_v2) 
    #  1.0 = palavras com o mesmo significado
    #  0.0 = palavras totalmente sem relação
    # -1.0 = palavras com sentidos opostos
    # quanto mais próximo de 1.0, mais próximas semanticamente são as palavras

VETORES_LIVRO = {}
ESTADO_JOGO = {
    "palavra_secreta": "",
    "ranking": [],
    "posicoes": {},
    "melhor_posicao": None,
    "dicas_dadas": [],
    "historico_tentativas": [],
    "total_tentativas": 0,
    "total_dicas": 0
}

# função para montar o ranking de palavras mais próximas da palavra sorteada
def montar_ranking(palavra_secreta):
    vetor_secreta = VETORES_LIVRO[palavra_secreta]
    ranking_temp = []
    
    for palavra, vetor in VETORES_LIVRO.items():
        if palavra == palavra_secreta:
            continue
        sim = calculo_similaridade(vetor_secreta, vetor)
        ranking_temp.append((palavra, sim))
        
    ranking_temp.sort(key=lambda x: x[1], reverse=True) # ordena do mais próximo para o mais distante
    ranking_temp.insert(0, (palavra_secreta, 1.0)) # a palavra sorteada fica no topo do ranking
    posicoes = {pal: idx + 1 for idx, (pal, _) in enumerate(ranking_temp)}
    
    return ranking_temp, posicoes

# função pra começar o jogo
def iniciar_partida():
    if not VETORES_LIVRO:
        return {"erro": "vetores nao carregados"}
        
    palavras = list(VETORES_LIVRO.keys())
    secreta = random.choice(palavras) # sorteia a palavra secreta
    ranking, posicoes = montar_ranking(secreta) # monta o ranking das palavras mais próximas da palavra secreta

    # sempre que iniciar uma nova partida, o estado do jogo é resetado
    ESTADO_JOGO["palavra_secreta"] = secreta
    ESTADO_JOGO["ranking"] = ranking
    ESTADO_JOGO["posicoes"] = posicoes
    ESTADO_JOGO["melhor_posicao"] = None
    ESTADO_JOGO["dicas_dadas"] = []
    ESTADO_JOGO["historico_tentativas"] = []
    ESTADO_JOGO["total_tentativas"] = 0
    ESTADO_JOGO["total_dicas"] = 0

    #alguns prints só pra visualizar o que tá acontecendo no servidor
    top5 = [pal for pal, _ in ranking[1:6]] 
    print("\n" + "=" * 40)
    print("partida iniciada!")
    print(f"palavra secreta (1): {secreta.upper()}")
    print(f"top 5 proximas: {', '.join(top5)}") # quando der play, ele printa a palavra secreta e as 5 mais próximas no terminal
    print("=" * 40 + "\n")
    
    return {
        "status": "partida iniciada",
        "total": len(ranking)
    }

# função para tentar adivinhar a palavra secreta
def tentar_palavra(palavra):
    if not ESTADO_JOGO["palavra_secreta"]:
        return {"erro": "nenhuma partida ativa"}
        
    palavra_proc = lematizar_palpite(palavra) 

    # verifica se a palavra chutada ou uma variação dela ja foi chutada e retorna um erro se for o caso
    ja_tentadas_lemas = [e["palavra"] for e in ESTADO_JOGO["historico_tentativas"]]
    if palavra_proc in ja_tentadas_lemas:
        return {"erro": f'A palavra "{palavra_proc}" (ou uma variação dela) já foi tentada!'}

    if palavra_proc not in ESTADO_JOGO["posicoes"]: # se a palavra chutada não estiver no vocabulário, rejeita e retorna um erro
        return {"erro": "Palavra não encontrada no universo do livro!"}
        
    posicao = ESTADO_JOGO["posicoes"][palavra_proc]
    similaridade = ESTADO_JOGO["ranking"][posicao - 1][1]

    # atualiza a melhor posição obtida até o momento, se a posição atual for melhor que a anterior
    if ESTADO_JOGO["melhor_posicao"] is None or posicao < ESTADO_JOGO["melhor_posicao"]: 
        ESTADO_JOGO["melhor_posicao"] = posicao

    ESTADO_JOGO["total_tentativas"] += 1
    
    registro = { # registra a tentativa do jogador no histórico de tentativas
        "palavra": palavra_proc,
        "posicao": posicao,
        "similaridade": round(similaridade, 4),
        "eh_dica": False
    }
    ESTADO_JOGO["historico_tentativas"].append(registro)
        
    return { # retorna as informações da tentativa para o cliente
        "palavra": palavra_proc,
        "posicao": posicao,
        "similaridade": round(similaridade, 4),
        "total": len(ESTADO_JOGO["ranking"]),
        "venceu": posicao == 1,
        "total_tentativas": ESTADO_JOGO["total_tentativas"],
        "total_dicas": ESTADO_JOGO["total_dicas"],
        "historico": ESTADO_JOGO["historico_tentativas"]
    }

# função para fornecer uma dica ao jogador
def pedir_dica():
    if not ESTADO_JOGO["palavra_secreta"]: # se não houver uma partida ativa, retorna um erro
        return {"erro": "nenhuma partida ativa"}
        
    ranking = ESTADO_JOGO["ranking"]
    secreta = ESTADO_JOGO["palavra_secreta"] 
    melhor = ESTADO_JOGO["melhor_posicao"] # posição da melhor tentativa do jogador até o momento 

    # um conjunto das palavras que ja apareceram como dica ou tentativas anteriores
    ja_exibidas = set(ESTADO_JOGO["dicas_dadas"]) | {e["palavra"] for e in ESTADO_JOGO["historico_tentativas"]}

    # se o jogador ainda não tiver chutado nada
    if melhor is None:
        candidatos = [ # pega as palavras entre a posição 151 e 250 do ranking
            pal for idx, (pal, _) in enumerate(ranking[150:250])
            if pal != secreta and pal not in ja_exibidas # filtra apenas palavras que não sejam a secreta e que ainda não tenham sido exibidas
        ]
        if not candidatos: # se não tiver candidatos nessa faixa, aceita qualquer palavra do top 200
            candidatos = [
                pal for idx, (pal, _) in enumerate(ranking[1:200])
                if pal != secreta and pal not in ja_exibidas 
            ]

    # se o jogador já tiver chutado alguma palavra ou pedido uma dica
    elif melhor > 2: 
        if melhor > 100: # se a melhor posição do jogador for maior que 100 a dica vai avançar 40 posições
            alvo = max(2, melhor - 40) 
        elif melhor > 30: # se a melhor posição do jogador for maior que 30 a dica vai avançar 15 posições
            alvo = max(2, melhor - 15)
        elif melhor > 10: # se a melhor posição do jogador for maior que 10 a dica vai avançar 5 posições
            alvo = max(2, melhor - 5)
        else: # se a melhor posição do jogador for menor ou igual a 10 a dica vai avançar 1 posição
            alvo = max(2, melhor - 1)

        faixa_min = max(2, alvo - 5) # trava a faixa mínima da dica para não ultrapassar a posição 2
        faixa_max = min(melhor - 1, alvo + 5) # trava pra não dar uma dica pior que a melhor posição do jogador
        
        candidatos = [ # filtra os candidatos dentro da janela calculada
            pal for idx, (pal, _) in enumerate(ranking[faixa_min - 1:faixa_max])
            if pal != secreta and pal not in ja_exibidas
        ]
        
        if not candidatos: # se não tiver candidatos nessa faixa aceita qualquer palavra entre a posição 2 e a melhor posição do jogador
            candidatos = [
                pal for idx, (pal, _) in enumerate(ranking[1:melhor - 1])
                if pal != secreta and pal not in ja_exibidas
            ]
    # se a melhor posição do jogador já for 2 a dica vai ser qualquer um entre 3 e 15
    else: 
        candidatos = [
            pal for idx, (pal, _) in enumerate(ranking[2:15])
            if pal != secreta and pal not in ja_exibidas
        ]
        if not candidatos: # se não tiver candidatos nessa faixa aceita qualquer palavra entre a posição 3 e 30
            candidatos = [
                pal for idx, (pal, _) in enumerate(ranking[2:30])
                if pal != secreta and pal not in ja_exibidas
            ]

    if not candidatos: # se não houver candidatos disponíveis, retorna uma mensagem de erro
        return {"erro": "sem mais dicas disponiveis"}

    dica = random.choice(candidatos) # escolhe aleatoriamente uma palavra candidata como dica
    ESTADO_JOGO["dicas_dadas"].append(dica)
    
    posicao = ESTADO_JOGO["posicoes"][dica]
    similaridade = ranking[posicao - 1][1]
    
    if ESTADO_JOGO["melhor_posicao"] is None or posicao < ESTADO_JOGO["melhor_posicao"]: # atualiza a melhor posição obtida se a posição da dica for melhor que a anterior
        ESTADO_JOGO["melhor_posicao"] = posicao

    ESTADO_JOGO["total_dicas"] += 1
    
    registro = { # registra a dica fornecida no histórico de tentativas
        "palavra": dica,
        "posicao": posicao,
        "similaridade": round(similaridade, 4),
        "eh_dica": True
    }
    ESTADO_JOGO["historico_tentativas"].append(registro)
    
    return { # retorna as informações da dica para o cliente
        "palavra": dica,
        "posicao": posicao,
        "similaridade": round(similaridade, 4),
        "total": len(ranking),
        "total_tentativas": ESTADO_JOGO["total_tentativas"],
        "total_dicas": ESTADO_JOGO["total_dicas"],
        "historico": ESTADO_JOGO["historico_tentativas"]
    }

# função para desistir da partida e revelar a palavra secreta
def desistir_partida():
    if not ESTADO_JOGO["palavra_secreta"]:
        return {"erro": "nenhuma partida ativa"}
        
    secreta = ESTADO_JOGO["palavra_secreta"]
    ranking = ESTADO_JOGO["ranking"]
    
    mais_proximas = [pal for pal, _ in ranking[1:6]] # pega as 5 palavras mais próximas da palavra secreta
    
    resposta = {
        "status": "partida encerrada",
        "palavra_secreta": secreta,
        "mais_proximas": mais_proximas,
        "total_tentativas": ESTADO_JOGO["total_tentativas"],
        "total_dicas": ESTADO_JOGO["total_dicas"]
    }
    
    ESTADO_JOGO["palavra_secreta"] = "" # reseta a palavra secreta para indicar que não há mais uma partida rolando
    return resposta

if __name__ == "__main__":
    vocabulario = preprocessar_livro()
    print("vocabulario processado")

    VETORES_LIVRO = carregar_vetores(vocabulario)
    print("vetores carregados")

    # função para gerar o arquivo do vocabulário (comentado pra não gerar sempre que rodar):

#    palavras_ordenadas = sorted(vocabulario.items())
#    caminho_saida = "vocabulario_gerado.txt"
#    with open(caminho_saida, "w", encoding="utf-8") as arquivo:
#        arquivo.write(f"VOCABULÁRIO COMPLETO: {len(vocabulario)} PALAVRAS\n")
#        for pal, freq in palavras_ordenadas:
#            arquivo.write(f"{pal:<20} : {freq}x\n")
#    print(f"arquivo '{caminho_saida}' gerado com sucesso")

    server = SimpleXMLRPCServer(("localhost", 9876)) # cria o servidor XML-RPC na porta 9876
    print("servidor iniciado")

    # funções que o cliente pode chamar remotamente:
    server.register_function(iniciar_partida, "iniciar_partida")
    server.register_function(tentar_palavra, "tentar_palavra")
    server.register_function(pedir_dica, "pedir_dica")
    server.register_function(desistir_partida, "desistir_partida")

    server.serve_forever()