"""Dicionário simples de entidades geográficas (correção do problema 1).

A base documental fala em região (Sul, Sudeste, Centro-Oeste, Nordeste,
Norte), mas uma pergunta real de atendente menciona a cidade do destino — sem
alguma forma de resolução cidade→região, "Manaus" nunca casa semanticamente
com "Norte" nem por embedding nem por cross-encoder (ver
resultados/03-problemas-e-correcoes.md, problema 1).
"""

import unicodedata

CITY_TO_REGION = {
    "manaus": "Norte",
    "belem": "Norte",
    "porto velho": "Norte",
    "boa vista": "Norte",
    "macapa": "Norte",
    "rio branco": "Norte",
    "palmas": "Norte",
    "salvador": "Nordeste",
    "recife": "Nordeste",
    "fortaleza": "Nordeste",
    "sao luis": "Nordeste",
    "natal": "Nordeste",
    "joao pessoa": "Nordeste",
    "maceio": "Nordeste",
    "aracaju": "Nordeste",
    "teresina": "Nordeste",
    "sao paulo": "Sudeste",
    "rio de janeiro": "Sudeste",
    "belo horizonte": "Sudeste",
    "vitoria": "Sudeste",
    "curitiba": "Sul",
    "porto alegre": "Sul",
    "florianopolis": "Sul",
    "brasilia": "Centro-Oeste",
    "goiania": "Centro-Oeste",
    "campo grande": "Centro-Oeste",
    "cuiaba": "Centro-Oeste",
}


def _normalize(text: str) -> str:
    text = text.lower()
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def expand_query(question: str) -> str:
    """Se a pergunta citar uma cidade conhecida, anexa uma frase natural
    ligando a cidade à região correspondente (não altera a pergunta mostrada
    ao LLM). Testado empiricamente contra o cross-encoder: uma frase natural
    ("Manaus fica na região Norte.") funciona bem melhor que uma tag entre
    parênteses ("(Região: Norte)") — o modelo foi treinado em texto corrido,
    não em anotações estruturadas."""
    normalized = _normalize(question)
    matched_cities = sorted({city for city in CITY_TO_REGION if city in normalized})
    if not matched_cities:
        return question
    hints = " ".join(f"{city.title()} fica na região {CITY_TO_REGION[city]}." for city in matched_cities)
    return f"{question} {hints}"
