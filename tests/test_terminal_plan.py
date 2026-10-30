import tempfile
import unittest
from pathlib import Path

from companera.application.commands import COMMANDS
from companera.interface.intro_sequence import INTRO_SEQUENCE, load_intro_frames
from companera.interface.layout import place_bubble, place_terminal
from companera.interface.screen_metrics import Rect
from companera.interface.terminal_render import parse_inline, wrap


class TerminalPlanTests(unittest.TestCase):
    def test_intro_sequence_exact_order(self):
        names = tuple(name for name, _ in INTRO_SEQUENCE)
        self.assertEqual(names, (
            "intro-grab", "intro-happy", "intro-mouth1", "intro-mouth2", "intro-mouth3",
            "intro-smear", "intro-wave1", "intro-wave2", "intro-wave3",
        ))

    def test_intro_missing_files_is_safe_and_equal_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            frames = load_intro_frames(Path(tmp), width=224)
        self.assertEqual(frames, [])

    def test_parse_inline(self):
        parsed = parse_inline("Hola **negrita** y `código`")
        self.assertIn(("bold", "negrita"), parsed)
        self.assertIn(("code", "código"), parsed)

    def test_wrap_respects_width_and_bullets(self):
        lines = wrap("- una respuesta bastante larga para probar el ancho", columns=24, prefix="")
        self.assertTrue(all(len(line) <= 24 for line in lines))
        self.assertTrue(lines[0].startswith("• "))

    def test_layout_terminal_left_and_bubble_no_overlap(self):
        monitor = Rect(0, 0, 1920, 1080)
        pet = Rect(1700, 400, 160, 160)
        terminal = place_terminal(pet, Rect(0, 0, 640, 440), monitor)
        bubble = place_bubble(pet, terminal, Rect(0, 0, 400, 260), monitor)
        self.assertEqual(terminal.right, pet.x - 16)
        self.assertFalse(
            bubble.x < terminal.right and bubble.x + bubble.w > terminal.x
            and bubble.y < terminal.y + terminal.h and bubble.y + bubble.h > terminal.y
        )

    def test_commands_have_no_extra_spaces(self):
        self.assertTrue(all(command == command.strip() for command in COMMANDS))


if __name__ == "__main__":
    unittest.main()
