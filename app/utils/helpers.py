"""
Funções utilitárias da API EAS.
"""
import hashlib
import re
import secrets
from datetime import datetime
from typing import List, Optional
import unicodedata


def generate_md5_key(prefix: str = "eas") -> str:
    """
    Gera uma API Key única usando MD5.

    Args:
        prefix: Prefixo para a key (default: "eas")

    Returns:
        API Key no formato: {prefix}_{hash_md5}
    """
    random_bytes = secrets.token_bytes(32)
    hash_md5 = hashlib.md5(random_bytes).hexdigest()
    return f"{prefix}_{hash_md5}"


def hash_api_key(api_key: str) -> str:
    """
    Gera hash MD5 de uma API Key para armazenamento.

    Args:
        api_key: API Key completa

    Returns:
        Hash MD5 da key
    """
    return hashlib.md5(api_key.encode()).hexdigest()


def validate_api_key(api_key: str) -> bool:
    """
    Valida formato de API Key.

    Args:
        api_key: API Key para validar

    Returns:
        True se válida, False caso contrário
    """
    if not api_key:
        return False

    # Formato esperado: prefix_hash (32 chars hex)
    parts = api_key.split("_")
    if len(parts) != 2:
        return False

    prefix, hash_part = parts
    if not prefix or len(prefix) > 10:
        return False

    if not re.match(r"^[a-f0-9]{32}$", hash_part):
        return False

    return True


def clean_text(text: str) -> str:
    """
    Limpa texto removendo caracteres especiais e normalizando.

    Args:
        text: Texto para limpar

    Returns:
        Texto limpo
    """
    if not text:
        return ""

    # Remove caracteres de controle
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)

    # Normaliza espaços em branco
    text = re.sub(r"\s+", " ", text)

    # Remove espaços extras nas pontas
    text = text.strip()

    # Normaliza unicode
    text = unicodedata.normalize("NFKC", text)

    return text


def extract_tags(text: str, max_tags: int = 10) -> List[str]:
    """
    Extrai tags relevantes de um texto.

    Args:
        text: Texto para extrair tags
        max_tags: Número máximo de tags

    Returns:
        Lista de tags extraídas
    """
    if not text:
        return []

    # Palavras-chave comuns em fitness/saúde
    keywords = {
        "treino", "exercicio", "musculo", "hipertrofia", "força",
        "nutricao", "dieta", "proteina", "carboidrato", "gordura",
        "suplemento", "creatina", "whey", "bcaa", "glutamina",
        "hormonio", "testosterona", "cortisol", "insulina",
        "esteroide", "anabolizante", "ciclo", "pct",
        "saude", "medico", "consulta", "exame",
        "cientifico", "estudo", "pesquisa", "artigo"
    }

    # Normaliza texto para lowercase
    text_lower = text.lower()

    # Encontra keywords presentes
    found_tags = []
    for keyword in keywords:
        if keyword in text_lower and keyword not in found_tags:
            found_tags.append(keyword)
            if len(found_tags) >= max_tags:
                break

    return found_tags


def format_datetime(dt: datetime) -> str:
    """
    Formata datetime para ISO 8601.

    Args:
        dt: datetime para formatar

    Returns:
        String formatada
    """
    return dt.isoformat() if dt else None


def parse_category(text: str) -> Optional[str]:
    """
    Detecta categoria baseado no conteúdo do texto.

    Args:
        text: Texto para análise

    Returns:
        Categoria detectada ou None
    """
    text_lower = text.lower()

    # Keywords por categoria
    category_keywords = {
        "treino": ["treino", "exercicio", "musculo", "hipertrofia", "força", "repeticao", "serie"],
        "nutricao": ["dieta", "nutricao", "caloria", "proteina", "carboidrato", "gordura", "macronutriente"],
        "suplementacao": ["suplemento", "creatina", "whey", "bcaa", "glutamina", "pre-treino"],
        "hormonios": ["hormonio", "testosterona", "cortisol", "insulina", "gh", "igf"],
        "esteroides": ["esteroide", "anabolizante", "aas", "ciclo", "pct", "hemogenin", "deca", "durabolin"],
        "medico": ["medico", "consulta", "exame", "diagnostico", "tratamento", "receita"],
        "cientifico": ["estudo", "pesquisa", "artigo", "cientifico", "pubmed", "scielo", "randomizado"],
        "tecnico": ["tecnica", "forma", "execucao", "biomecanica", "artrologia"]
    }

    # Conta matches por categoria
    matches = {}
    for category, keywords in category_keywords.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > 0:
            matches[category] = count

    # Retorna categoria com mais matches
    if matches:
        return max(matches, key=matches.get)

    return "geral"