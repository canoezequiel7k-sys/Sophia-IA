import json
from datetime import datetime
from pathlib import Path

from companera.domain.models import CheckIn, Mood, Topic


class JsonMemoryRepository:
    def __init__(self, path: Path):
        self._path = path

    def _read(self) -> list[CheckIn]:
        if not self._path.exists():
            return []
        with self._path.open(encoding="utf-8") as file:
            records = json.load(file)
        if not isinstance(records, list):
            raise ValueError(f"El archivo de memoria debe contener una lista: {self._path}")
        return [
            CheckIn(
                text=item["text"],
                mood=Mood(item["mood"]),
                topic=Topic(item["topic"]),
                created_at=datetime.fromisoformat(item["created_at"]),
            )
            for item in records
        ]

    def latest(self) -> CheckIn | None:
        records = self._read()
        return records[-1] if records else None

    def save(self, check_in: CheckIn) -> None:
        records = self._read()
        records.append(check_in)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as file:
            json.dump(
                [
                    {
                        "text": item.text,
                        "mood": item.mood.value,
                        "topic": item.topic.value,
                        "created_at": item.created_at.isoformat(),
                    }
                    for item in records
                ],
                file,
                ensure_ascii=False,
                indent=2,
            )
