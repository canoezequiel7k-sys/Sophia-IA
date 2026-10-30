import json
import tempfile
import unittest
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from companera.application.chat_service import ChatService
from companera.application.tools import Permission, ToolRegistry
from companera.domain.models import CheckIn, Mood, Reply, Topic
from companera.infrastructure.gemini_service import GeminiService
from companera.infrastructure.json_memory_repository import JsonMemoryRepository
from companera.infrastructure.settings import Settings
from companera.infrastructure.speech_text import clean_for_speech
from companera.infrastructure.voice_service import VoiceService


class FixedClock:
    def now(self):
        return datetime(2026, 1, 1, tzinfo=timezone.utc)


class FakeLanguageModel:
    def __init__(self, reply: Reply): self.reply = reply
    def generate_reply(self, text, history=None): return self.reply


class AudioFake:
    def __init__(self):
        class MixerMusic:
            def load(self, path): self.loaded = path
            def play(self): self.played = True
            def get_busy(self): return False
            def stop(self): return
        class Mixer:
            def __init__(self): self.music = MixerMusic()
            def init(self): return
        self.mixer = Mixer()


class CoreTests(unittest.TestCase):
    def test_speech_cleaning(self):
        cleaned = clean_for_speech("*Hola* https://ejemplo.com ```print('x')``` 😄")
        self.assertNotIn("*", cleaned)
        self.assertNotIn("😄", cleaned)
        self.assertIn("un enlace", cleaned)
        self.assertIn("te dejé el código en el chat", cleaned)

    def test_settings_invalid_values_are_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text("{}", encoding="utf-8")
            settings = Settings.load(path)
            self.assertTrue(settings.voice_enabled)
            self.assertEqual(settings.avatar_size, 160)

    def test_chat_service_does_not_save_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory = JsonMemoryRepository(Path(tmp) / "memoria.json")
            service = ChatService(memory, FixedClock(), FakeLanguageModel(Reply("falló", ok=False, error_code="network")))
            reply = service.send("hola")
            self.assertFalse(reply.ok)
            self.assertEqual(memory.history(), [])

    def test_tool_limit_and_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = ToolRegistry(Path(tmp), [])
            registry.reset()
            confirmed = registry.run("get_datetime", confirm=lambda _: False)
            self.assertIsInstance(confirmed, str)
            for _ in range(3):
                registry.run("get_datetime")
            self.assertIn("límite", registry.run("get_datetime"))

    def test_read_file_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = ToolRegistry(root, [str(root / "permitida")])
            result = registry.read_text_file("../secreto.txt")
            self.assertIn("rechazada", result)

    def test_read_text_file_happy_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            permitted = root / "permitida"
            permitted.mkdir()
            source = permitted / "nota.txt"
            source.write_text("Hola desde el archivo", encoding="utf-8")
            registry = ToolRegistry(root, [str(permitted)])
            result = registry.run("read_text_file", confirm=lambda _: True, path=str(source))
            self.assertEqual(result, "Hola desde el archivo")

    def test_voice_cancel_generation_does_not_play(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            def generator(text=None, path=None):
                def run(): Path(path).write_bytes(b"fake")
                return run
            voice = VoiceService(cache_dir=path / "cache", tts_generator=generator, audio_backend=AudioFake())
            voice.speak("hola")
            voice.stop()
            self.assertFalse(voice.is_speaking())

    @patch("urllib.request.urlopen")
    def test_invalid_key_is_typed_error_and_header_has_key(self, mock_open):
        error = urllib.error.HTTPError("https://example.test", 401, "Unauthorized", {}, None)
        mock_open.side_effect = error
        service = GeminiService(api_key="secreto_no_loguear", project_root=Path("/no_existe"))
        reply = service.generate_reply("hola")
        self.assertFalse(reply.ok)
        self.assertEqual(reply.error_code, "invalid_key")
        request = mock_open.call_args.args[0]
        self.assertNotIn("secreto_no_loguear", request.full_url)
        self.assertEqual(request.headers["X-goog-api-key"], "secreto_no_loguear")


if __name__ == "__main__":
    unittest.main()
