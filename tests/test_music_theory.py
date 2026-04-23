"""Unit tests for compiler.music_theory helpers."""

import unittest

from compiler.music_theory import (
    chord_compatible_with_key,
    note_in_scale,
    solfege_to_midi,
)


class TestSolfegeToMidi(unittest.TestCase):
    """Validate note-string to MIDI conversion."""

    def test_la3(self) -> None:
        self.assertEqual(solfege_to_midi("La3"), 57)

    def test_do4(self) -> None:
        self.assertEqual(solfege_to_midi("Do4"), 60)

    def test_sol_sharp3(self) -> None:
        self.assertEqual(solfege_to_midi("Sol#3"), 56)

    def test_re_flat4(self) -> None:
        self.assertEqual(solfege_to_midi("Réb4"), 61)

    def test_invalid_format_raises(self) -> None:
        with self.assertRaises(ValueError):
            solfege_to_midi("A4")


class TestNoteInScale(unittest.TestCase):
    """Validate scale membership checks."""

    def test_note_in_la_mineur_true(self) -> None:
        self.assertTrue(note_in_scale("La3", "La mineur"))

    def test_note_out_of_la_mineur_false(self) -> None:
        self.assertFalse(note_in_scale("Sol#3", "La mineur"))

    def test_note_in_do_majeur_true(self) -> None:
        self.assertTrue(note_in_scale("Do4", "Do majeur"))

    def test_unknown_scale_is_permissive(self) -> None:
        self.assertTrue(note_in_scale("Fa#4", "Scale inconnue"))

    def test_invalid_note_string_false(self) -> None:
        self.assertFalse(note_in_scale("??", "La mineur"))


class TestChordCompatibility(unittest.TestCase):
    """Validate chord/key compatibility lookup."""

    def test_la_mineur_in_la_mineur(self) -> None:
        self.assertTrue(chord_compatible_with_key("La_mineur", "La mineur"))

    def test_do_majeur_in_la_mineur(self) -> None:
        self.assertTrue(chord_compatible_with_key("Do_majeur", "La mineur"))

    def test_fa_mineur_not_in_la_mineur(self) -> None:
        self.assertFalse(chord_compatible_with_key("Fa_mineur", "La mineur"))

    def test_re_mineur_in_do_majeur(self) -> None:
        self.assertTrue(chord_compatible_with_key("Ré_mineur", "Do majeur"))

    def test_unknown_key_is_permissive(self) -> None:
        self.assertTrue(chord_compatible_with_key("AnyChord", "Unknown key"))


if __name__ == "__main__":
    unittest.main()
