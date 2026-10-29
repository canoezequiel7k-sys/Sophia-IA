import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from companera.domain.models import CheckIn

DEFAULT_MODEL = "gemini-3.1-flash-lite-preview"
FALLBACK_MODELS = [
    "gemini-3.1-flash-lite-preview",
    "gemini-3-flash-preview",
]
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

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
Al final de CADA respuesta debés poner EXACTAMENTE UNA etiqueta de expresión, sin excepción:
  [EXPR: calm]  → respuesta tranquila, cotidiana o reflexiva
  [EXPR: laugh] → alegría, broma, entusiasmo o algo divertido
  [EXPR: smug]  → logro, ingenio, picardía o tip con actitud
  [EXPR: look]  → curiosidad genuina, pregunta o interés en algo que dijeron
  [EXPR: aside] → análisis cuidadoso, algo delicado o revisando un error
  [EXPR: wide]  → sorpresa, descubrimiento o algo inesperado
  [EXPR: many]  → confusión cómica, desconcierto o situación absurda

La etiqueta va siempre al final, nunca en el medio del texto.\
"""

VALID_EXPRESSIONS = frozenset({"calm", "laugh", "smug", "look", "aside", "wide", "many"})


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
        """Ejecuta una llamada POST a la API y devuelve el JSON de respuesta."""
        url = API_URL.format(model=model, key=self._api_key)
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    def generate_reply(
        self,
        user_message: str,
        history: list[CheckIn] | None = None,
    ) -> tuple[str, str]:
        """Envía el mensaje a Gemini y devuelve (texto_limpio, expresión).

        Si la API no está configurada, devuelve un mensaje de aviso amistoso.
        Si un modelo está descontinuado, intenta el siguiente de la lista de respaldo.
        """
        if not self.is_configured:
            return (
                "Todavía no tengo mi clave de Gemini configurada en el `.env`. "
                "Agregá `GEMINI_API_KEY=tu_clave` y reiniciame para que pueda hablar de verdad.",
                "aside",
            )

        # Construir historial de conversación (últimos 8 turnos)
        contents: list[dict[str, Any]] = []
        if history:
            for item in history[-8:]:
                contents.append({"role": "user", "parts": [{"text": item.text}]})
                if item.reply:
                    contents.append({"role": "model", "parts": [{"text": item.reply}]})
        contents.append({"role": "user", "parts": [{"text": user_message}]})

        payload: dict[str, Any] = {
            "system_instruction": {"parts": [{"text": SOPHIA_SYSTEM_PROMPT}]},
            "contents": contents,
            "generationConfig": {"temperature": 0.8, "maxOutputTokens": 800},
        }

        models_to_try = [self._model] + [m for m in FALLBACK_MODELS if m != self._model]
        last_error = ""

        for model_name in models_to_try:
            try:
                result = self._post(model_name, payload)
                break
            except urllib.error.HTTPError as err:
                body = err.read().decode("utf-8", errors="replace")
                last_error = f"HTTP {err.code}"
                if err.code in (404, 400):
                    continue  # modelo descontinuado, intentar el siguiente
                return (f"Tuve un problema con Gemini ({err.code}): {body[:100]}...", "aside")
            except Exception as err:
                last_error = str(err)
                continue
        else:
            return (f"No pude conectar con Gemini. Último error: {last_error[:100]}", "aside")

        # Extraer texto de la respuesta
        try:
            raw = result["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError):
            return ("No pude interpretar la respuesta del servidor.", "calm")

        # Separar expresión del texto
        match = re.search(r"\[EXPR:\s*([a-zA-Z]+)\]\s*$", raw)
        if match:
            expr = match.group(1).lower()
            text = raw[: match.start()].strip()
        else:
            expr = "calm"
            text = raw

        return text, expr if expr in VALID_EXPRESSIONS else "calm"
