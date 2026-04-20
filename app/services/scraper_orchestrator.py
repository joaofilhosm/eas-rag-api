"""
Orquestrador do Scraper com IA.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio

from openai import AsyncOpenAI

from app.config import get_settings
from database import db


class ScraperOrchestrator:
    """
    Orquestrador do scraper que usa IA para decidir
    o que extrair de cada página.
    """

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(
            base_url=settings.openrouter_base_url,
            api_key=settings.openrouter_api_key
        )
        self.default_model = settings.default_model

    async def extract_content(
        self,
        html: str,
        url: str,
        source_type: str = "general"
    ) -> Optional[Dict[str, Any]]:
        """
        Usa IA para extrair conteúdo estruturado de HTML.

        Args:
            html: HTML da página
            url: URL da página
            source_type: Tipo da fonte (fitness, scientific, etc)

        Returns:
            Dicionário com título, conteúdo e metadados
        """
        # Limita HTML para não exceder tokens
        html_content = html[:15000] if len(html) > 15000 else html

        prompt = f"""Analise o seguinte HTML de uma página web e extraia as informações relevantes.

URL: {url}
Tipo de conteúdo: {source_type}

HTML:
{html_content}

Extraia:
1. Título principal do conteúdo
2. Conteúdo completo e relevante (artigo, texto principal)
3. Categoria apropriada (treino, nutricao, suplementacao, hormonios, esteroides, medico, cientifico, tecnico, geral)
4. Tags relevantes (palavras-chave)
5. Metadados importantes (autor, data, etc)

Responda APENAS com JSON válido no formato:
{{
    "titulo": "título extraído",
    "conteudo": "conteúdo completo extraído",
    "categoria": "categoria",
    "tags": ["tag1", "tag2"],
    "metadata": {{
        "autor": "autor se disponível",
        "data": "data se disponível",
        "outros": "outros metadados relevantes"
    }},
    "relevante": true/false
}}

Se o conteúdo não for relevante (ex: página de login, erro, conteúdo duplicado), marque "relevante": false.
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": "Você é um especialista em extração de dados web. Sempre responda com JSON válido."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )

            import json

            content = response.choices[0].message.content

            # Remove markdown code blocks se presentes
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            result = json.loads(content.strip())

            if not result.get("relevante", True):
                return None

            return {
                "titulo": result.get("titulo", "Sem título"),
                "conteudo": result.get("conteudo", ""),
                "categoria": result.get("categoria", "geral"),
                "tags": result.get("tags", []),
                "metadata": result.get("metadata", {}),
                "url_original": url
            }

        except Exception as e:
            # Fallback: tenta extrair com BeautifulSoup
            return await self._fallback_extract(html, url)

    async def _fallback_extract(
        self,
        html: str,
        url: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extração de fallback usando BeautifulSoup.

        Args:
            html: HTML da página
            url: URL da página

        Returns:
            Dicionário com dados extraídos
        """
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, 'lxml')

            # Tenta encontrar título
            titulo = None
            for tag in ['h1', 'title']:
                if soup.find(tag):
                    titulo = soup.find(tag).get_text(strip=True)
                    break

            if not titulo:
                titulo = "Sem título"

            # Tenta encontrar conteúdo principal
            conteudo = None
            for tag in ['article', 'main', 'div.content', 'div.post-content', 'div.entry-content']:
                element = soup.select_one(tag)
                if element:
                    conteudo = element.get_text(strip=True)
                    break

            if not conteudo:
                # Pega todo o texto do body
                if soup.body:
                    conteudo = soup.body.get_text(strip=True)[:5000]
                else:
                    return None

            # Limita conteúdo
            if len(conteudo) > 10000:
                conteudo = conteudo[:10000]

            return {
                "titulo": titulo[:500],
                "conteudo": conteudo,
                "categoria": "geral",
                "tags": [],
                "metadata": {},
                "url_original": url
            }

        except Exception as e:
            return None

    async def extract_scientific_content(
        self,
        html: str,
        url: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extrai conteúdo de artigos científicos.

        Args:
            html: HTML da página
            url: URL da página

        Returns:
            Dicionário com dados do artigo
        """
        prompt = f"""Analise o seguinte HTML de um artigo científico e extraia as informações relevantes.

URL: {url}

HTML:
{html[:20000]}

Extraia:
1. Título do artigo
2. Autores
3. Resumo (abstract)
4. Palavras-chave
5. Ano de publicação
6. Journal/Fonte

Responda APENAS com JSON válido:
{{
    "titulo": "título do artigo",
    "conteudo": "resumo e informações principais",
    "categoria": "cientifico",
    "tags": ["palavra-chave1", "palavra-chave2"],
    "metadata": {{
        "autores": ["autor1", "autor2"],
        "ano": "ano",
        "journal": "journal",
        "doi": "doi se disponível"
    }},
    "relevante": true/false
}}
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": "Você é um especialista em análise de artigos científicos. Sempre responda com JSON válido."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )

            import json

            content = response.choices[0].message.content

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            result = json.loads(content.strip())

            if not result.get("relevante", True):
                return None

            return {
                "titulo": result.get("titulo", "Sem título"),
                "conteudo": result.get("conteudo", ""),
                "categoria": "cientifico",
                "tags": result.get("tags", []),
                "metadata": result.get("metadata", {}),
                "url_original": url
            }

        except Exception as e:
            return await self._fallback_extract(html, url)


# Instância global
scraper_orchestrator = ScraperOrchestrator()