from pathlib import Path

from companera.infrastructure.gemini_service import GeminiService
from companera.infrastructure.json_memory_repository import JsonMemoryRepository
from companera.infrastructure.system_clock import SystemClock
from companera.interface.desktop_pet import start_desktop


def main() -> None:
    """Lanza Sophia IA en modo escritorio."""
    start_desktop()


if __name__ == "__main__":
    main()
