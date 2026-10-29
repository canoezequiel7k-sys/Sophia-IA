import json
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from companera.domain.models import CheckIn, Mood, Topic


class JsonMemoryRepository:
    """Persiste los intercambios de Sophia en un archivo JSON local."""

    LEGACY_TOPIC_MAP = {
        "programación": Topic.TECHNICAL,
        "programacion": Topic.TECHNICAL,
        "trabajo": Topic.TECHNICAL,
        "estudio": Topic.TECHNICAL,
        "familia": Topic.PERSONAL,
        "relaciones": Topic.PERSONAL,
        "salud": Topic.PERSONAL,
        "programming": Topic.TECHNICAL,
        "work": Topic.TECHNICAL,
        "family": Topic.PERSONAL,
    }

    def __init__(self, path: Path) -> None:
        self._path = path

    def _coerce_topic(self, raw_topic: object) -> Topic:
        if isinstance(raw_topic, Topic):
            return raw_topic
        try:
            return Topic(str(raw_topic))
        except (TypeError, ValueError):
            normalized = str(raw_topic).strip().casefold()
            if normalized in self.LEGACY_TOPIC_MAP:
                return self.LEGACY_TOPIC_MAP[normalized]
            return Topic.GENERAL

    def _read(self) -> list[CheckIn]:
        """Lee todos los recuerdos del archivo. Lanza ValueError si está dañado."""
        if not self._path.exists():
            return []
        try:
            records = json.loads(self._path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"La memoria JSON está dañada: {self._path}") from error
        if not isinstance(records, list):
            raise ValueError(f"El archivo de memoria debe contener una lista: {self._path}")
        result = []
        for item in records:
            try:
                mood = Mood(item.get("mood", "calm"))
            except ValueError:
                mood = Mood.CALM
            topic = self._coerce_topic(item.get("topic", "general"))
            result.append(CheckIn(
                text=item["text"],
                mood=mood,
                topic=topic,
                created_at=datetime.fromisoformat(item["created_at"]),
                reply=item.get("reply", ""),
            ))
        return result

    def latest(self) -> CheckIn | None:
        """Devuelve el intercambio más reciente, o None si no hay ninguno."""
        records = self._read()
        return records[-1] if records else None

    def history(self) -> list[CheckIn]:
        """Devuelve todos los intercambios guardados."""
        return self._read()

    def save(self, check_in: CheckIn) -> None:
        """Agrega un nuevo intercambio usando escritura atómica."""
        records = self._read()
        records.append(check_in)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp: Path | None = None
        try:
            with NamedTemporaryFile(
                "w", encoding="utf-8", dir=self._path.parent, delete=False, suffix=".json"
            ) as f:
                tmp = Path(f.name)
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
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
                f.write("\n")
            tmp.replace(self._path)
        finally:
            if tmp is not None and tmp.exists():
                tmp.unlink(missing_ok=True)

    def clear(self) -> None:
        """Borra toda la memoria local."""
        if self._path.exists():
            self._path.unlink()
