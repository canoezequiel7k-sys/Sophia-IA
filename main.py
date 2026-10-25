from pathlib import Path

from companera.application.companion import CheckInUseCase
from companera.infrastructure.json_memory_repository import JsonMemoryRepository
from companera.infrastructure.keyword_text_analyzer import KeywordTextAnalyzer
from companera.infrastructure.system_clock import SystemClock
from companera.interface.console import run_companion


def main() -> None:
    memory = JsonMemoryRepository(Path(__file__).parent / "data" / "memoria.json")
    run_companion(CheckInUseCase(memory, KeywordTextAnalyzer(), SystemClock()))


if __name__ == "__main__":
    main()
