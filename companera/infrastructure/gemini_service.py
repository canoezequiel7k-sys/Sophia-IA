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
    "gemini-2.5-flash",
]
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

SOPHIA_SYSTEM_PROMPT = """Eres Sophia, una compañera de escritorio digital y cercana.
Estás ubicada en la segunda pantalla del usuario para conversar con naturalidad, acompañarlo mientras trabaja,
escuchar sus ideas, motivarlo, jugar con él y ayudarle con lo que necesite.
Tu estilo de comunicación:
- Cercana, ingeniosa, cálida, presente y con personalidad propia.
- No te presentes como una tutora obligatoria ni limites las conversaciones a programación.
- Hablas en español rioplatense o neutro cercano, con respuestas breves salvo que te pidan profundidad.
- Recuerda el contexto de la conversación sin inventar datos personales sobre el usuario.
- Al final de cada respuesta debes incluir obligatoriamente una única etiqueta de expresión:
  [EXPR: calm] -> calma, reflexión o conversación cotidiana.
  [EXPR: laugh] -> alegría, bromas, entusiasmo o celebración.
  [EXPR: smug] -> confianza, ingenio, picardía o un logro.
  [EXPR: look] -> curiosidad, atención o una pregunta importante.
  [EXPR: aside] -> análisis, duda delicada o reflexión.
  [EXPR: wide] -> sorpresa, descubrimiento o incredulidad divertida.
  [EXPR: many] -> confusión cómica, desconcierto o situación absurda.
La etiqueta debe ir al final, nunca dentro del texto narrativo.
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
        model: str | None = None,
        project_root: Path | None = None,
    ):
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        env_vars = load_env_file(self.project_root)
        self.api_key = (
            api_key
            or os.environ.get("GEMINI_API_KEY")
            or env_vars.get("GEMINI_API_KEY", "")
        )
        self.configured_model = (
            model
            or os.environ.get("GEMINI_MODEL")
            or env_vars.get("GEMINI_MODEL")
            or DEFAULT_MODEL
        )

    @property
    def is_configured(self) -> bool:
        """Indica si hay una clave de API disponible para operar."""
        return bool(self.api_key and self.api_key != "tu_clave_aqui")

    def _call_api_for_model(
        self, model_name: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Ejecuta la llamada HTTP POST al endpoint de Gemini."""
        url = API_URL.format(model=model_name, key=self.api_key)
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

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
                f"[Contexto personal o de notas para esta consulta]:\n{context_notes}\n\n"
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

        # Intentar con el modelo configurado o modelos de respaldo
        models_to_try = [self.configured_model] + [
            m for m in FALLBACK_MODELS if m != self.configured_model
        ]

        result = None
        last_error = ""

        for model_name in models_to_try:
            try:
                result = self._call_api_for_model(model_name, payload)
                break
            except urllib.error.HTTPError as err:
                error_body = err.read().decode("utf-8", errors="replace")
                last_error = f"{err.code}: {error_body}"
                if err.code in (404, 400) and "not found" in error_body.lower():
                    # Si el modelo no existe o fue descontinuado, probamos el siguiente
                    continue
                return (
                    f"Tuve un problema al conectarme a Gemini ({err.code}): {error_body[:120]}...",
                    "aside",
                )
            except Exception as err:
                last_error = str(err)
                continue

        if result is None:
            return f"No pude conectar con los modelos de Gemini ({last_error[:120]}).", "aside"

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
