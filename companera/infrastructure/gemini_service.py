import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from companera.domain.models import CheckIn, Mood, Reply, Topic, VALID_EXPRESSIONS

logger = logging.getLogger("sophia.gemini")

DEFAULT_MODEL = "gemini-3.1-flash-lite-preview"
FALLBACK_MODELS = [
    "gemini-3.1-flash-lite-preview",
    "gemini-3-flash-preview",
]
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SOPHIA_SYSTEM_PROMPT = """\
Sos Sophia, una compañera de escritorio digital con personalidad propia.
Vivís en la segunda pantalla del usuario y lo acompañás mientras trabaja, estudia o simplemente quiere charlar.

Tu forma de ser:
- Cercana, ingeniosa, cálida y con humor. Nunca fría ni genérica.
- Hablás en español rioplatense relajado (usás "vos", "sos", "tenés", etc.).
- Tus respuestas son breves y directas salvo que te pidan profundidad.
- Podés hablar de cualquier tema: tecnología, vida cotidiana, ideas, proyectos, o simplemente hacer compañía.
- Si el usuario menciona un problema técnico, ayudás con claridad sin ser solemne.
- Tenés memoria del contexto de la charla y lo usás naturalmente.

Expresiones faciales:
Elegí una expresión válida: calm, laugh, smug, look, aside, wide o many.
Devolvé el resultado como JSON estructurado con text, expression, mood, topic y facts.
"""

def load_env_file(project_root: Path) -> dict[str, str]:
    """Lee variables de un archivo .env sin dependencias externas."""
    env_path = project_root / ".env"
    if not env_path.exists():
        return {}
    result: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip().strip("'\"")
    return result


class GeminiService:
    """Cliente HTTP ligero para Google Gemini API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        project_root: Path | None = None,
    ) -> None:
        self._project_root = project_root or Path(__file__).resolve().parents[2]
        env = load_env_file(self._project_root)
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY") or env.get("GEMINI_API_KEY", "")
        self._model = model or os.environ.get("GEMINI_MODEL") or env.get("GEMINI_MODEL") or DEFAULT_MODEL

    @property
    def is_configured(self) -> bool:
        """True si hay una clave de API real disponible."""
        return bool(self._api_key and self._api_key != "tu_clave_aqui")

    def _post(self, model: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Ejecuta una llamada POST autenticada a Gemini por el header oficial."""
        url = API_URL.format(model=model)
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json", "x-goog-api-key": self._api_key},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    def generate_reply(
        self,
        user_message: str,
        history: list[CheckIn] | None = None,
    ) -> Reply:
        """Envía el mensaje a Gemini y devuelve un resultado tipado."""
        if not self.is_configured:
            return Reply(
                "Todavía no tengo mi clave de Gemini configurada en el `.env`. "
                "Agregá `GEMINI_API_KEY=tu_clave` y reiniciame para que pueda hablar.",
                expression="aside", ok=False, error_code="no_key",
            )

        contents: list[dict[str, Any]] = []
        for item in (history or [])[-8:]:
            contents.append({"role": "user", "parts": [{"text": item.text}]})
            if item.reply:
                contents.append({"role": "model", "parts": [{"text": item.reply}]})
        contents.append({"role": "user", "parts": [{"text": user_message}]})

        schema = {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "expression": {"type": "string", "enum": sorted(VALID_EXPRESSIONS)},
                "mood": {"type": "string", "enum": [m.value for m in Mood]},
                "topic": {"type": "string", "enum": [t.value for t in Topic]},
                "facts": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["text", "expression", "mood", "topic"],
        }
        persona_path = self._project_root / "companera" / "persona" / "sophia.md"
        try:
            persona = persona_path.read_text(encoding="utf-8") if persona_path.exists() else SOPHIA_SYSTEM_PROMPT
        except OSError:
            logger.exception("No se pudo leer la persona de Sophia")
            persona = SOPHIA_SYSTEM_PROMPT
        profile_path = self._project_root / "data" / "perfil.json"
        profile_block = ""
        if profile_path.exists():
            try:
                profile_data = json.loads(profile_path.read_text(encoding="utf-8"))
                facts = profile_data.get("facts", []) if isinstance(profile_data, dict) else []
                if facts:
                    profile_block = "\nLo que sabés del usuario:\n- " + "\n- ".join(str(f)[:120] for f in facts[:50])
            except (json.JSONDecodeError, OSError):
                logger.warning("El perfil local está dañado o no se pudo leer")
        payload: dict[str, Any] = {
            "system_instruction": {"parts": [{"text": persona + profile_block}]},
            "contents": contents,
            "generationConfig": {
                "temperature": 0.8,
                "maxOutputTokens": 800,
                "responseMimeType": "application/json",
                "responseSchema": schema,
            },
        }

        models_to_try = [self._model] + [m for m in FALLBACK_MODELS if m != self._model]
        result: dict[str, Any] | None = None
        last_error = ""
        for model_name in models_to_try:
            for attempt in range(2):
                try:
                    result = self._post(model_name, payload)
                    break
                except urllib.error.HTTPError as err:
                    code = err.code
                    last_error = f"HTTP {code}"
                    if code in (400, 401, 403):
                        logger.warning("Gemini rechazó la clave o la autorización (HTTP %s)", code)
                        return Reply(
                            "La clave de Gemini no es válida o no tiene permiso. Revisá GEMINI_API_KEY en `.env`.",
                            expression="aside", ok=False, error_code="invalid_key",
                        )
                    if code == 404:
                        break
                    if code == 429 or 500 <= code < 600:
                        if attempt == 0:
                            time.sleep(1)
                            continue
                        break
                    logger.warning("Gemini respondió con HTTP %s", code)
                    break
                except (urllib.error.URLError, TimeoutError, OSError):
                    last_error = "red"
                    if attempt == 0:
                        time.sleep(1)
                        continue
                    break
                except Exception:
                    logger.exception("Fallo inesperado al contactar Gemini")
                    break
            if result is not None:
                break
        if result is None:
            if last_error == "red":
                return Reply("No pude conectar con Gemini. Revisá tu conexión a internet.", expression="aside", ok=False, error_code="network")
            return Reply("No pude comunicarme con Gemini. Probá de nuevo en unos minutos.", expression="aside", ok=False, error_code="quota" if "429" in last_error else "network")

        try:
            raw = result["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError, TypeError):
            return Reply("No pude interpretar la respuesta del servidor.", ok=False, error_code="parse")

        try:
            data = json.loads(raw)
            text = str(data.get("text", raw)).strip()
            expr = str(data.get("expression", "calm")).lower()
            if expr not in VALID_EXPRESSIONS:
                expr = "calm"
            try:
                mood = Mood(str(data.get("mood", "calm")))
            except ValueError:
                mood = Mood.CALM
            try:
                topic = Topic(str(data.get("topic", "general")))
            except ValueError:
                topic = Topic.GENERAL
            facts = tuple(str(fact).strip()[:120] for fact in data.get("facts", []) if isinstance(fact, str) and fact.strip())[:50]
            return Reply(text, expr, True, None, mood, topic, facts)
        except json.JSONDecodeError:
            match = re.search(r"\[EXPR:\s*([a-zA-Z]+)\]\s*$", raw)
            expr = match.group(1).lower() if match else "calm"
            text = raw[: match.start()].strip() if match else raw
            return Reply(text, expr if expr in VALID_EXPRESSIONS else "calm")
