import re
import unicodedata
from pathlib import Path

from companera.application.knowledge import KnowledgeEntry


def _normalize(text: str) -> str:
    """Ignora mayúsculas y tildes para encontrar alias con facilidad."""
    text = unicodedata.normalize("NFD", text.casefold())
    return "".join(char for char in text if unicodedata.category(char) != "Mn")


def _summary(content: str) -> str:
    """Saca una explicación corta para mostrar antes de abrir toda la nota."""
    match = re.search(r"\*\*Qué es:\*\*\s*(.*?)(?=\n\n|\Z)", content, re.IGNORECASE | re.DOTALL)
    if match:
        return re.sub(r"\s+", " ", match.group(1)).strip()
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith(("#", "-", "**", "---")):
            return line
    return "Hay una entrada sobre este tema."


class MarkdownKnowledgeBase:
    """Busca temas y alias en los apuntes Markdown guardados en el proyecto."""
    def __init__(self, directory: Path):
        self._directory = directory

    def _entries(self) -> list[KnowledgeEntry]:
        """Lee las secciones que empiezan con ## sin cambiar los archivos."""
        entries = []
        for path in sorted(self._directory.rglob("*.md")):
            text = path.read_text(encoding="utf-8-sig")
            sections = re.split(r"(?m)(?=^##\s+)", text)
            for section in sections:
                heading = re.match(r"##\s+(.+)", section)
                if not heading:
                    continue
                title = heading.group(1).strip()
                content = section.strip()
                alias_match = re.search(
                    r"(?im)^-\s*\*\*alias:\*\*\s*(.+)$", content
                )
                aliases = alias_match.group(1).split(",") if alias_match else []
                entries.append(
                    KnowledgeEntry(
                        title=title,
                        summary=_summary(content),
                        content=content,
                        source=path.name,
                    )
                )
        return entries

    def search(self, query: str, limit: int = 5) -> list[KnowledgeEntry]:
        """Prioriza el tema y sus alias por encima de menciones casuales."""
        query_normalized = _normalize(query).strip()
        terms = set(re.findall(r"[a-z0-9_]+", query_normalized))
        # Quitamos palabras de la pregunta para quedarnos con el tema buscado.
        ignored = {
            "estoy", "viendo", "sobre", "tema", "explica", "que", "es",
            "de", "el", "la", "si", "s",
        }
        terms -= ignored
        if not terms:
            return []
        ranked = []
        for entry in self._entries():
            searchable = _normalize(entry.title)
            content = _normalize(entry.content)
            aliases_match = re.search(
                r"(?im)^-\s*\*\*alias:\*\*\s*(.+)$", entry.content
            )
            aliases = {
                _normalize(alias.strip())
                for alias in aliases_match.group(1).split(",")
            } if aliases_match else set()
            score = 0
            for term in terms:
                if term == searchable:
                    score += 10
                elif term in aliases:
                    score += 9
                elif term in searchable:
                    score += 7
                elif re.search(rf"\b{re.escape(term)}\b", content):
                    score += 1
            if score:
                ranked.append((score, entry))
        ranked.sort(key=lambda result: (-result[0], result[1].title.casefold()))
        exact_matches = [entry for score, entry in ranked if score >= 7]
        if exact_matches:
            return exact_matches[:limit]
        return [entry for _, entry in ranked[:limit]]
