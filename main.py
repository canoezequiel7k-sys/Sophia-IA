from pathlib import Path

from companera.application.companion import CheckInUseCase
from companera.application.knowledge import (
    RecordInteractionUseCase,
    SearchKnowledgeUseCase,
)
from companera.infrastructure.json_memory_repository import JsonMemoryRepository
from companera.infrastructure.keyword_text_analyzer import KeywordTextAnalyzer
from companera.infrastructure.markdown_knowledge_base import MarkdownKnowledgeBase
from companera.infrastructure.system_clock import SystemClock
from companera.interface.console import run_companion


def main() -> None:
    project_root = Path(__file__).parent
    memory = JsonMemoryRepository(project_root / "data" / "memoria.json")
    knowledge = SearchKnowledgeUseCase(
        MarkdownKnowledgeBase(project_root / "companera" / "python context")
    )
    run_companion(
        CheckInUseCase(memory, KeywordTextAnalyzer(), SystemClock()),
        memory,
        knowledge,
        RecordInteractionUseCase(memory, SystemClock()),
    )


if __name__ == "__main__":
    main()
