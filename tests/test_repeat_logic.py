"""Tests focused on repeat and measure-range logic alignment."""

import unittest

from compiler.codegen import MIDIGenerator
from compiler.parser import parse
from compiler.semantic import analyze


class TestRepeatLogic(unittest.TestCase):
    """Validate measure range repetition and repeat behavior."""

    def test_measure_range_duration_matches_battery_cycle(self) -> None:
        source = '''
        piste "Range Repeat" {
          batterie {
            mesure {
              kick: [X . . . X . . .]
            }
            répéter 1
          }

          mélodie instrument: piano {
            mesure 1..4 {
              note(La3, noire)
            }
          }
        }
        '''
        ast, parse_msgs = parse(source)
        self.assertIsNotNone(ast)
        self.assertFalse(any(m.level == "error" for m in parse_msgs))
        assert ast is not None

        sem_msgs = analyze(ast)
        mismatch_warnings = [m for m in sem_msgs if m.level == "warning" and "lengths differ" in m.message]
        self.assertEqual(
            len(mismatch_warnings),
            0,
            "Expected no mismatch warning when melody range repeats to same total beats as battery cycle.",
        )

    def test_codegen_measure_range_repeats_notes(self) -> None:
        source = '''
        piste "Codegen Repeat" {
          mélodie instrument: piano {
            mesure 1..4 {
              note(La3, noire)
            }
          }
        }
        '''
        ast, parse_msgs = parse(source)
        self.assertIsNotNone(ast)
        self.assertFalse(any(m.level == "error" for m in parse_msgs))
        assert ast is not None

        sem_msgs = analyze(ast)
        self.assertFalse(any(m.level == "error" for m in sem_msgs))

        gen = MIDIGenerator()
        gen.generate(ast, "output/test_repeat_logic.mid")
        assert gen._midi is not None

        # MIDIEventList stores note-on/note-off events. 4 repeated notes produce at least 4 note-on events.
        note_on_events = []
        for track in gen._midi.tracks:
          for event in track.eventList:
            if getattr(event, "evtname", "") == "NoteOn":
              note_on_events.append(event)
        self.assertGreaterEqual(len(note_on_events), 4)


if __name__ == "__main__":
    unittest.main()
