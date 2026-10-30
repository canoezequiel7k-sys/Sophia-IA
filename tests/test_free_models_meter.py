from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from companera.application.model_router import ModelRouter
from companera.domain.models import TokenUsage
from companera.infrastructure.profile_store import ProfileStore
from companera.infrastructure.settings import Settings
from companera.infrastructure.usage_tracker import UsageTracker


class FreeModelsAndMeterTests(unittest.TestCase):
    def test_profiles_include_free_providers_and_local(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profiles, fallback = ProfileStore(root, "gemini-test").load()
            ids = {p.id for p in profiles}
            self.assertIn("gemini-lite", ids)
            self.assertIn("groq-free", ids)
            self.assertIn("openrouter-free", ids)
            self.assertIn("mistral-free", ids)
            self.assertIn("ollama-local", ids)
            self.assertTrue((root / "data" / "models.json").exists())
            self.assertEqual(fallback, ["gemini-lite"])

    def test_usage_tracks_successful_requests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tracker = UsageTracker(Path(tmp) / "uso.json")
            now = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
            tracker.record("gemini-lite", TokenUsage(prompt=1000, completion=300, total=1300), now)
            tracker.record("gemini-lite", TokenUsage(prompt=800, completion=200, total=1000), now)
            today = tracker.today("gemini-lite", now)
            self.assertEqual(today.requests, 2)
            self.assertEqual(today.prompt, 1800)
            self.assertEqual(today.completion, 500)
            self.assertEqual(today.total, 2300)
            self.assertEqual(today.last_total, 1000)

    def test_missing_active_key_returns_no_key_not_network(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            settings = Settings(active_model="gemini-lite")
            router = ModelRouter(root, settings=settings)
            reply = router.generate_reply("hola")
            self.assertFalse(reply.ok)
            self.assertEqual(reply.error_code, "no_key")
            self.assertIn("Falta configurar", reply.text)


if __name__ == "__main__":
    unittest.main()
