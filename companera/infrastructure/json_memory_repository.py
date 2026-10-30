import json
import logging
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from companera.domain.models import CheckIn, Mood, Topic

logger = logging.getLogger("sophia.memory")


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
        """Lee recuerdos válidos y pone en cuarentena un archivo dañado."""
        if not self._path.exists():
            return []
        try:
            records = json.loads(self._path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            quarantine = self._path.with_name(f"memoria.corrupta-{timestamp}.json")
            try:
                self._path.rename(quarantine)
                logger.warning("Memoria dañada puesta en cuarentena: %s", quarantine.name)
            except OSError:
                logger.exception("No se pudo poner la memoria dañada en cuarentena")
            return []
        except OSError:
            logger.exception("No se pudo leer el archivo de memoria")
            return []
        if not isinstance(records, list):
            logger.warning("El archivo de memoria no contiene una lista; se ignora")
            return []
        result: list[CheckIn] = []
        for item in records:
            if not isinstance(item, dict):
                continue
            if not all(key in item for key in ("text", "created_at")):
                continue
            try:
                try:
                    mood = Mood(item.get("mood", "calm"))
                except ValueError:
                    mood = Mood.CALM
                topic = self._coerce_topic(item.get("topic", "general"))
                result.append(CheckIn(
                    text=str(item["text"]),
                    mood=mood,
                    topic=topic,
                    created_at=datetime.fromisoformat(str(item["created_at"])),
                    reply=str(item.get("reply", "")),
                ))
            except (TypeError, ValueError, KeyError):
                logger.warning("Se omitió un registro incompleto o inválido de memoria")
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
        except (OSError, TypeError, ValueError):
            logger.exception("No se pudo guardar la memoria")
            raise
        finally:
            if tmp is not None and tmp.exists():
                tmp.unlink(missing_ok=True)

    def clear(self) -> None:
        """Borra toda la memoria local."""
        if self._path.exists():
            self._path.unlink()
