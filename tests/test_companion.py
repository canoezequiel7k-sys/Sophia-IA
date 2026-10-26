import json
import io
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from companera.application.companion import CheckInUseCase
from companera.application.knowledge import (
    RecordInteractionUseCase,
    SearchKnowledgeUseCase,
)
from companera.domain.models import Mood, Topic
from companera.infrastructure.json_memory_repository import JsonMemoryRepository
from companera.infrastructure.keyword_text_analyzer import KeywordTextAnalyzer
from companera.infrastructure.markdown_knowledge_base import MarkdownKnowledgeBase
from companera.interface.console import run_companion


class FixedClock:
    """Reloj fijo para que las pruebas den siempre el mismo resultado."""

    def now(self):
        """Devuelve la fecha establecida para estas pruebas."""
        return datetime(2026, 1, 1, tzinfo=timezone.utc)


class CompanionTests(unittest.TestCase):
    """Comprueba la conversación y la búsqueda sin usar datos personales."""
    def setUp(self):
        """Crea archivos temporales que se limpian al terminar cada prueba."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.path = Path(self.temp_dir.name) / "memoria.json"
        self.memory = JsonMemoryRepository(self.path)
        self.analyzer = KeywordTextAnalyzer()
        self.clock = FixedClock()
        self.companion = CheckInUseCase(self.memory, self.analyzer, self.clock)
        self.record_interaction = RecordInteractionUseCase(self.memory, self.clock)
        self.knowledge_dir = Path(self.temp_dir.name) / "python context"
        self.knowledge_dir.mkdir()
        (self.knowledge_dir / "fundamentos.md").write_text(
            "# Python\n\n## string\n"
            "- **alias:** string, strings, str, cadena\n"
            "- **categoria:** fundamentos\n\n"
            "**Qué es:** Texto inmutable usado para representar caracteres.\n\n"
            "**Ejemplo:** `nombre = \"Ana\"`\n",
            encoding="utf-8",
        )
        self.knowledge = SearchKnowledgeUseCase(
            MarkdownKnowledgeBase(self.knowledge_dir)
        )

    def test_analyzes_mood_topic_and_accents(self):
        """Comprueba ánimo, tema y palabras con tildes."""
        self.assertEqual(
            self.analyzer.analyze("Estoy feliz por mi trabajo"),
            (Mood.HAPPY, Topic.WORK),
        )
        self.assertEqual(
            self.analyzer.analyze("Estoy cansada por el examen"),
            (Mood.TIRED, Topic.STUDY),
        )
        self.assertEqual(
            self.analyzer.analyze("Tengo un error en mi código Python"),
            (Mood.CALM, Topic.PROGRAMMING),
        )

    def test_python_question_prompts_for_reproducible_details(self):
        """La ayuda de Python pregunta qué ocurrió y pide el error completo."""
        reply = self.companion.respond("Tengo un error en mi código Python")
        self.assertIn("paso a paso", reply.text)
        self.assertIn("mensaje completo", reply.text)

    def test_negation_does_not_assign_negated_mood(self):
        """Una palabra negada no se toma como el ánimo de la persona."""
        self.assertEqual(
            self.analyzer.analyze("No estoy triste, estoy feliz")[0],
            Mood.HAPPY,
        )

    def test_replies_with_topic_question_and_saves_both_sides(self):
        """Comprueba que la respuesta y el mensaje quedan guardados."""
        reply = self.companion.respond("Estoy triste por mi familia")
        saved = self.memory.latest()
        self.assertIn("¿Qué pasó con tu familia?", reply.text)
        self.assertEqual(reply.user_mood, Mood.SAD.value)
        self.assertEqual(saved.text, "Estoy triste por mi familia")
        self.assertEqual(saved.reply, reply.text)

    def test_previous_mood_is_recalled_after_reloading_memory(self):
        """Verifica que un recuerdo se conserva al abrir la memoria otra vez."""
        self.companion.respond("Estoy triste")
        reloaded = CheckInUseCase(
            JsonMemoryRepository(self.path), self.analyzer, FixedClock()
        )
        reply = reloaded.respond("Ahora estoy feliz")
        self.assertIn("La última vez te sentías triste", reply.text)

    def test_history_and_clear(self):
        """Comprueba que se puede consultar y borrar el historial."""
        self.companion.respond("Estoy feliz")
        self.companion.respond("Estoy cansado")
        self.assertEqual(len(self.memory.history()), 2)
        self.memory.clear()
        self.assertEqual(self.memory.history(), [])

    def test_corrupt_memory_reports_clear_error(self):
        """Una memoria rota se reporta, no se oculta."""
        self.path.write_text("{invalido", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "memoria JSON está dañada"):
            self.memory.latest()

    def test_reads_old_records_without_reply(self):
        """La memoria antigua sigue funcionando aunque no tenga respuesta."""
        self.path.write_text(
            json.dumps(
                [{
                    "text": "Estoy bien",
                    "mood": "happy",
                    "topic": "general",
                    "created_at": "2026-01-01T00:00:00+00:00",
                }]
            ),
            encoding="utf-8",
        )
        self.assertEqual(self.memory.latest().reply, "")

    def test_console_conversation_memory_and_confirmed_delete(self):
        """Simula comandos de terminal y el borrado confirmado."""
        output = io.StringIO()
        answers = iter([
            "/ayuda",
            "Estoy feliz por el trabajo",
            "/memoria",
            "/borrar",
            "sí",
            "/memoria",
            "salir",
        ])
        with patch("builtins.input", side_effect=lambda _prompt: next(answers)):
            with patch("sys.stdout", output):
                run_companion(
                    self.companion,
                    self.memory,
                    self.knowledge,
                    self.record_interaction,
                )
        self.assertIn("¿Qué fue lo que más te afectó del trabajo hoy?", output.getvalue())
        self.assertIn("Recuerdo 1 conversaciones", output.getvalue())
        self.assertIn("borré mis recuerdos", output.getvalue())
        self.assertEqual(self.memory.history(), [])

    def test_searches_markdown_alias_and_returns_entry_context(self):
        """Un alias permite encontrar la nota y su contexto."""
        matches = self.knowledge.execute("Estoy viendo Strings")
        self.assertEqual(matches[0].title, "string")
        self.assertIn("Texto inmutable", matches[0].summary)
        self.assertIn("**Ejemplo:**", matches[0].content)

    def test_console_shows_summary_and_full_context_after_yes(self):
        """El contexto completo solo aparece si la persona responde que sí."""
        output = io.StringIO()
        answers = iter(["Estoy viendo Strings", "sí", "salir"])
        with patch("builtins.input", side_effect=lambda _prompt: next(answers)):
            with patch("sys.stdout", output):
                run_companion(
                    self.companion,
                    self.memory,
                    self.knowledge,
                    self.record_interaction,
                )
        self.assertIn("¿Querés que te muestre el contexto completo", output.getvalue())
        self.assertIn("**Ejemplo:** `nombre = \"Ana\"`", output.getvalue())
        self.assertEqual(len(self.memory.history()), 2)

    def test_console_normalizes_uppercase_greeting_and_confirmation(self):
        """Mayúsculas y tildes no cambian cómo se entienden las respuestas."""
        output = io.StringIO()
        answers = iter(["HOLA", "GRACIAS", "SÍ", "NO NECESITO NADA MÁS"])
        with patch("builtins.input", side_effect=lambda _prompt: next(answers)):
            with patch("sys.stdout", output):
                run_companion(
                    self.companion,
                    self.memory,
                    self.knowledge,
                    self.record_interaction,
                )
        text = output.getvalue()
        self.assertIn("¡Hola! ¿Qué necesitás?", text)
        self.assertIn("¡De nada! ¿Necesitás algo más?", text)
        self.assertIn("Claro, decime qué necesitás.", text)
        self.assertIn("Está bien. Hasta pronto.", text)

    def test_console_closes_on_cierrate(self):
        """La orden de cierre también funciona con mayúsculas."""
        output = io.StringIO()
        with patch("builtins.input", return_value="CIÉRRATE"):
            with patch("sys.stdout", output):
                run_companion(
                    self.companion,
                    self.memory,
                    self.knowledge,
                    self.record_interaction,
                )
        self.assertIn("Hasta pronto.", output.getvalue())

    def test_console_opens_only_fixed_windows_terminal_command(self):
        """Una petición de terminal usa wt.exe sin ejecutar texto del mensaje."""
        output = io.StringIO()
        answers = iter(["SOP -TERMINAL", "NO NECESITO NADA MÁS"])
        with patch("builtins.input", side_effect=lambda _prompt: next(answers)):
            with patch("shutil.which", return_value="C:\\Windows\\wt.exe"):
                with patch("subprocess.Popen") as popen:
                    with patch("sys.stdout", output):
                        run_companion(
                            self.companion,
                            self.memory,
                            self.knowledge,
                            self.record_interaction,
                        )
        popen.assert_called_once_with(
            ["C:\\Windows\\wt.exe", "-w", "new"], shell=False
        )
        self.assertIn("terminal nueva de Windows", output.getvalue())

    def test_help_clear_and_close_commands(self):
        """Los comandos cortos muestran ayuda, limpian pantalla y cierran."""
        output = io.StringIO()
        answers = iter(["SOP -HELP", "CLEAR", "SOP -CLOSE"])
        with patch("builtins.input", side_effect=lambda _prompt: next(answers)):
            with patch("os.system") as system:
                with patch("sys.stdout", output):
                    run_companion(
                        self.companion,
                        self.memory,
                        self.knowledge,
                        self.record_interaction,
                    )
        system.assert_called_once_with("cls")
        self.assertIn("sop -new", output.getvalue())
        self.assertIn("\033[93mclear\033[0m", output.getvalue())
        self.assertIn("Hasta pronto.", output.getvalue())

    def test_new_sophia_terminal_starts_application_without_shell(self):
        """El comando de nueva sesión abre Sophia con argumentos separados."""
        output = io.StringIO()
        answers = iter(["SOP -NEW", "NO NECESITO NADA MÁS"])
        with patch("builtins.input", side_effect=lambda _prompt: next(answers)):
            with patch("shutil.which", return_value="C:\\Windows\\wt.exe"):
                with patch("subprocess.Popen") as popen:
                    with patch("sys.stdout", output):
                        run_companion(
                            self.companion,
                            self.memory,
                            self.knowledge,
                            self.record_interaction,
                        )
        command = popen.call_args.args[0]
        self.assertEqual(command[:3], ["C:\\Windows\\wt.exe", "-w", "new"])
        self.assertTrue(command[-1].endswith("main.py"))
        self.assertFalse(popen.call_args.kwargs["shell"])
        self.assertIn("otra terminal con Sophia IA", output.getvalue())


if __name__ == "__main__":
    unittest.main()
