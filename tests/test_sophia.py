import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from companera.domain.models import CheckIn, Mood, Topic, VALID_EXPRESSIONS
from companera.infrastructure.gemini_service import GeminiService, load_env_file
from companera.infrastructure.json_memory_repository import JsonMemoryRepository


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Memoria
# ---------------------------------------------------------------------------

class MemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._path = Path(self._tmp.name) / "memoria.json"
        self._repo = JsonMemoryRepository(self._path)

    def _make_check_in(self, text: str = "Hola", reply: str = "¡Hola!") -> CheckIn:
        return CheckIn(text=text, mood=Mood.CALM, topic=Topic.GENERAL,
                       created_at=FixedClock().now(), reply=reply)

    def test_empty_repository_returns_none(self) -> None:
        self.assertIsNone(self._repo.latest())
        self.assertEqual(self._repo.history(), [])

    def test_save_and_retrieve(self) -> None:
        ci = self._make_check_in()
        self._repo.save(ci)
        self.assertEqual(self._repo.latest(), ci)
        self.assertEqual(len(self._repo.history()), 1)

    def test_clear_removes_all_records(self) -> None:
        self._repo.save(self._make_check_in())
        self._repo.save(self._make_check_in("Adiós"))
        self._repo.clear()
        self.assertEqual(self._repo.history(), [])
        self.assertIsNone(self._repo.latest())

    def test_corrupt_file_is_quarantined(self) -> None:
        self._path.write_text("{roto", encoding="utf-8")
        self.assertIsNone(self._repo.latest())
        self.assertFalse(self._path.exists())
        self.assertTrue(any(self._path.parent.glob("memoria.corrupta-*.json")))

    def test_persists_across_instances(self) -> None:
        ci = self._make_check_in("Persistencia")
        self._repo.save(ci)
        reloaded = JsonMemoryRepository(self._path)
        self.assertEqual(reloaded.latest().text, "Persistencia")

    def test_topic_migration_defaults_to_general(self) -> None:
        """Registros antiguos sin campo topic usan 'general' por defecto."""
        self._path.write_text(json.dumps([{
            "text": "Hola",
            "mood": "calm",
            "created_at": "2026-01-01T00:00:00+00:00",
            "reply": "",
        }]), encoding="utf-8")
        ci = self._repo.latest()
        self.assertEqual(ci.topic, Topic.GENERAL)

    def test_legacy_programming_topic_migrates_without_error(self) -> None:
        self._path.write_text(json.dumps([{
            "text": "Hola",
            "mood": "calm",
            "topic": "programación",
            "created_at": "2026-01-01T00:00:00+00:00",
            "reply": "Hola",
        }]), encoding="utf-8")
        ci = self._repo.latest()
        self.assertEqual(ci.topic, Topic.TECHNICAL)
        self._repo.save(self._make_check_in("Nueva charla"))
        self.assertEqual(self._repo.latest().topic, Topic.GENERAL)

    def test_reply_defaults_to_empty_string(self) -> None:
        self._path.write_text(json.dumps([{
            "text": "Sin reply",
            "mood": "calm",
            "topic": "general",
            "created_at": "2026-01-01T00:00:00+00:00",
        }]), encoding="utf-8")
        self.assertEqual(self._repo.latest().reply, "")

    def test_saves_multiple_entries_in_order(self) -> None:
        for i in range(5):
            self._repo.save(self._make_check_in(f"Mensaje {i}"))
        history = self._repo.history()
        self.assertEqual(len(history), 5)
        self.assertEqual(history[-1].text, "Mensaje 4")


# ---------------------------------------------------------------------------
# GeminiService
# ---------------------------------------------------------------------------

class EnvFileTests(unittest.TestCase):
    def test_parses_key_value_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(
                "GEMINI_API_KEY=abc123\n# comentario\nOTRA=valor\n",
                encoding="utf-8",
            )
            env = load_env_file(root)
        self.assertEqual(env["GEMINI_API_KEY"], "abc123")
        self.assertEqual(env["OTRA"], "valor")

    def test_missing_env_file_returns_empty_dict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_env_file(Path(tmp)), {})

    def test_strips_quotes_from_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text("KEY='entre_comillas'\n", encoding="utf-8")
            env = load_env_file(root)
        self.assertEqual(env["KEY"], "entre_comillas")


class GeminiUnconfiguredTests(unittest.TestCase):
    def test_is_configured_false_without_key(self) -> None:
        svc = GeminiService(api_key=None, project_root=Path("/no_existe"))
        self.assertFalse(svc.is_configured)

    def test_is_configured_false_with_placeholder(self) -> None:
        svc = GeminiService(api_key="tu_clave_aqui", project_root=Path("/no_existe"))
        self.assertFalse(svc.is_configured)

    def test_unconfigured_returns_friendly_aside_message(self) -> None:
        svc = GeminiService(api_key=None, project_root=Path("/no_existe"))
        reply = svc.generate_reply("Hola")
        self.assertEqual(reply.expression, "aside")
        self.assertFalse(reply.ok)
        self.assertEqual(reply.error_code, "no_key")
        self.assertIn("GEMINI_API_KEY", reply.text)


class GeminiConfiguredTests(unittest.TestCase):
    def _mock_response(self, text: str) -> MagicMock:
        resp = MagicMock()
        resp.read.return_value = json.dumps({
            "candidates": [{"content": {"parts": [{"text": text}]}}]
        }).encode("utf-8")
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    @patch("urllib.request.urlopen")
    def test_parses_expression_tag(self, mock_open: MagicMock) -> None:
        mock_open.return_value = self._mock_response("¡Hola! ¿Cómo estás? [EXPR: laugh]")
        svc = GeminiService(api_key="valid_key_123", project_root=Path("/no_existe"))
        reply = svc.generate_reply("Hola")
        self.assertEqual(reply.expression, "laugh")
        self.assertEqual(reply.text, "¡Hola! ¿Cómo estás?")

    @patch("urllib.request.urlopen")
    def test_missing_expression_tag_falls_back_to_calm(self, mock_open: MagicMock) -> None:
        mock_open.return_value = self._mock_response("Texto sin tag")
        svc = GeminiService(api_key="valid_key_123", project_root=Path("/no_existe"))
        reply = svc.generate_reply("Hola")
        self.assertEqual(reply.expression, "calm")

    @patch("urllib.request.urlopen")
    def test_unknown_expression_tag_falls_back_to_calm(self, mock_open: MagicMock) -> None:
        mock_open.return_value = self._mock_response("Texto [EXPR: xyz]")
        svc = GeminiService(api_key="valid_key_123", project_root=Path("/no_existe"))
        reply = svc.generate_reply("Hola")
        self.assertEqual(reply.expression, "calm")
        self.assertEqual(reply.text, "Texto")

    @patch("urllib.request.urlopen")
    def test_structured_target_is_parsed(self, mock_open: MagicMock) -> None:
        structured = json.dumps({
            "text": "Mirate el reloj.", "expression": "smug", "mood": "happy",
            "topic": "general", "facts": [], "title": "Hora actual",
            "target": "clock", "target_label": "RELOJ",
        })
        mock_open.return_value = self._mock_response(structured)
        reply = GeminiService(api_key="valid_key_123", project_root=Path("/no_existe")).generate_reply("qué hora es")
        self.assertEqual(reply.title, "Hora actual")
        self.assertEqual(reply.target, "clock")
        self.assertEqual(reply.target_label, "RELOJ")

    @patch("urllib.request.urlopen")
    def test_structured_invalid_target_falls_back_to_none(self, mock_open: MagicMock) -> None:
        structured = json.dumps({
            "text": "Sin señalador.", "expression": "calm", "mood": "calm",
            "topic": "general", "facts": [], "title": "Aviso",
            "target": "moon", "target_label": "LUNA",
        })
        mock_open.return_value = self._mock_response(structured)
        reply = GeminiService(api_key="valid_key_123", project_root=Path("/no_existe")).generate_reply("hola")
        self.assertEqual(reply.target, "none")

    @patch("urllib.request.urlopen")
    def test_all_valid_expressions_accepted(self, mock_open: MagicMock) -> None:
        svc = GeminiService(api_key="valid_key_123", project_root=Path("/no_existe"))
        for expression in VALID_EXPRESSIONS:
            mock_open.return_value = self._mock_response(f"Respuesta. [EXPR: {expression}]")
            reply = svc.generate_reply("test")
            self.assertEqual(reply.expression, expression, f"Expresión '{expression}' debería ser válida")

    @patch("urllib.request.urlopen")
    def test_history_is_included_in_payload(self, mock_open: MagicMock) -> None:
        mock_open.return_value = self._mock_response("Ok [EXPR: calm]")
        history = [
            CheckIn("hola", Mood.CALM, Topic.GENERAL, datetime(2026, 1, 1), "hola también"),
        ]
        svc = GeminiService(api_key="valid_key_123", project_root=Path("/no_existe"))
        svc.generate_reply("¿Recordás lo anterior?", history=history)
        call_body = json.loads(mock_open.call_args[0][0].data.decode())
        self.assertGreater(len(call_body["contents"]), 1)


if __name__ == "__main__":
    unittest.main()
