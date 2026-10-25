import json
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from companera.domain.models import CheckIn, Mood, Topic


class JsonMemoryRepository:
    def __init__(self, path: Path):
        self._path = path

    def _read(self) -> list[CheckIn]:
        if not self._path.exists():
            return []
        try:
            with self._path.open(encoding="utf-8") as file:
                records = json.load(file)
        except json.JSONDecodeError as error:
            raise ValueError(f"La memoria JSON está dañada: {self._path}") from error
        if not isinstance(records, list):
            raise ValueError(f"El archivo de memoria debe contener una lista: {self._path}")
        return [
            CheckIn(
                text=item["text"],
                mood=Mood(item["mood"]),
                topic=Topic(item["topic"]),
                created_at=datetime.fromisoformat(item["created_at"]),
                reply=item.get("reply", ""),
            )
            for item in records
        ]

    def latest(self) -> CheckIn | None:
        records = self._read()
        return records[-1] if records else None

    def history(self) -> list[CheckIn]:
        return self._read()

    def save(self, check_in: CheckIn) -> None:
        records = self._read()
        records.append(check_in)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = None
        try:
            with NamedTemporaryFile(
                "w", encoding="utf-8", dir=self._path.parent, delete=False
            ) as file:
                temporary_path = Path(file.name)
                json.dump(
                    [
                        {
                            "text": item.text,
                            "mood": item.mood.value,
                            "topic": item.topic.value,
                            "created_at": item.created_at.isoformat(),
                            "reply": item.reply,
                        }
                        for item in records
                    ],
                    file,
                    ensure_ascii=False,
                    indent=2,
                )
                file.write("\n")
            temporary_path.replace(self._path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def clear(self) -> None:
        if self._path.exists():
            self._path.unlink()
