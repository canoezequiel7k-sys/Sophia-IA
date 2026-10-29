import io
import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from companera.domain.models import CheckIn, Mood, Topic
from companera.infrastructure.gemini_service import GeminiService, load_env_file


class GeminiServiceTests(unittest.TestCase):
    def test_load_env_file(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir)
            (path / ".env").write_text(
                "GEMINI_API_KEY=test_key_123\nOTHER_VAR='hello'\n# comment\n",
                encoding="utf-8",
            )
            env = load_env_file(path)
            self.assertEqual(env.get("GEMINI_API_KEY"), "test_key_123")
            self.assertEqual(env.get("OTHER_VAR"), "hello")

    def test_unconfigured_returns_friendly_prompt(self):
        service = GeminiService(api_key=None, project_root=Path("/empty"))
        reply, expr = service.generate_reply("Hola Sophia")
        self.assertIn("Aún no tengo configurada mi clave", reply)
        self.assertEqual(expr, "calm")

    @patch("urllib.request.urlopen")
    def test_successful_reply_parsing_expression(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": "¡Hola! ¿En qué andás programando hoy? [EXPR: smug]"
                                }
                            ]
                        }
                    }
                ]
            }
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        service = GeminiService(api_key="valid_key")
        reply, expr = service.generate_reply("Hola")
        self.assertEqual(reply, "¡Hola! ¿En qué andás programando hoy?")
        self.assertEqual(expr, "smug")


if __name__ == "__main__":
    unittest.main()
