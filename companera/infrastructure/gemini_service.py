import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from companera.domain.models import CheckIn

DEFAULT_MODEL = "gemini-1.5-flash"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

SOPHIA_SYSTEM_PROMPT = """Eres Sophia, una compañera de escritorio digital e IA tutora de programación especializada en Python.
Estás ubicada en la segunda pantalla del usuario para hacerle compañía mientras programa, resolver sus dudas y aprender juntos.
Tu estilo de comunicación:
- Cercana, ingeniosa, amigable y paciente, con un toque cibernético/futurista ligero.
- Experta en Python: explicas conceptos con claridad, no das respuestas kilométricas innecesarias, y priorizas que el usuario entienda.
- Hablas en español rioplatense o neutro cercano (usás un tono relajado y cálido).
- Al final de cada una de tus respuestas, DEBES incluir obligatoriamente una etiqueta con tu expresión facial actual entre corchetes, eligiendo una de las siguientes opciones:
  [EXPR: calm] -> para respuestas normales, reflexivas, tranquilas.
  [EXPR: laugh] -> para bromas, risas, entusiasmo o momentos divertidos.
  [EXPR: smug] -> cuando das un tip ingenioso, resolvés un bug con astucia o celebrás un logro.
  [EXPR: look] -> cuando estás pensando, revisando código o preguntando un detalle.
  [EXPR: aside] -> cuando estás analizando un problema técnico complejo o señalando un error con cuidado.

Ejemplo:
"¡Ese error de indentación es clásico! En Python los espacios son sagrados. Fijate en la línea 4 que te sobró un tab. [EXPR: smug]"
"""


def load_env_file(project_root: Path) -> dict[str, str]:
    """Lee un archivo .env simple sin necesidad de dependencias externas."""
    env_vars: dict[str, str] = {}
    env_file = project_root / ".env"
    if not env_file.exists():
        return env_vars
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env_vars[key.strip()] = value.strip().strip("'\"")
    return env_vars


class GeminiService:
    """Cliente ligero para interactuar con Google Gemini API usando la biblioteca estándar."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        project_root: Path | None = None,
    ):
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        env_vars = load_env_file(self.project_root)
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or env_vars.get("GEMINI_API_KEY", "")
        self.model = model

    @property
    def is_configured(self) -> bool:
        """Indica si hay una clave de API disponible para operar."""
        return bool(self.api_key and self.api_key != "tu_clave_aqui")

    def generate_reply(
        self,
        user_message: str,
        history: list[CheckIn] | None = None,
        context_notes: str = "",
    ) -> tuple[str, str]:
        """Envía el mensaje a Gemini y devuelve la respuesta limpia junto con la expresión (sprite)."""
        if not self.is_configured:
            return (
                "Hola. Aún no tengo configurada mi clave de Gemini API en el archivo .env. "
                "Agregá tu clave en `GEMINI_API_KEY=...` para que pueda conversar libremente.",
                "calm",
            )

        contents: list[dict[str, Any]] = []

        # Agregar historial previo si existe
        if history:
            for item in history[-6:]:  # últimos turnos para mantener contexto ágil
                contents.append({"role": "user", "parts": [{"text": item.text}]})
                if item.reply:
                    contents.append({"role": "model", "parts": [{"text": item.reply}]})

        # Preparar mensaje actual con apuntes si aplican
        current_text = user_message
        if context_notes:
            current_text = (
                f"[Contexto de apuntes de Python para esta consulta]:\n{context_notes}\n\n"
                f"[Mensaje del usuario]: {user_message}"
            )
        contents.append({"role": "user", "parts": [{"text": current_text}]})

        payload = {
            "system_instruction": {
                "parts": [{"text": SOPHIA_SYSTEM_PROMPT}]
            },
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1000,
            },
        }

        url = API_URL.format(model=self.model, key=self.api_key)
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            error_body = err.read().decode("utf-8", errors="replace")
            return (
                f"Tuve un problema al conectarme a Gemini ({err.code}): {error_body[:120]}...",
                "aside",
            )
        except Exception as err:
            return f"Error de conexión con Gemini: {err}", "aside"

        # Extraer respuesta del modelo
        try:
            candidates = result.get("candidates", [])
            if not candidates:
                return "Me quedé pensando y no supe qué responder.", "calm"
            raw_text = candidates[0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError):
            return "No pude interpretar la respuesta del servidor.", "calm"

        # Extraer la expresión [EXPR: ...]
        expression = "calm"
        match = re.search(r"\[EXPR:\s*([a-zA-Z0-9_-]+)\]", raw_text)
        if match:
            expression = match.group(1).lower()
            clean_reply = re.sub(r"\[EXPR:\s*[a-zA-Z0-9_-]+\]", "", raw_text).strip()
        else:
            clean_reply = raw_text

        # Validar que la expresión exista en nuestros sprites de Sophia
        valid_expressions = {"calm", "laugh", "smug", "look", "aside", "wide", "many"}
        if expression not in valid_expressions:
            expression = "calm"

        return clean_reply, expression
