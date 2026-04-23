"""Parser feature tests for expressions, variables, and conditions."""

import unittest

from compiler.parser import parse
from compiler.ast_nodes import NoteNode


class TestParserFeatures(unittest.TestCase):
    """Validate newly added parser language features."""

    def test_variable_expression_in_effects(self) -> None:
        source = '''
        piste "Expr" {
          v = 0.5
          batterie {
            mesure {
              kick: [X . . .]
            }
            effets { volume: v + 0.25 }
            répéter 2
          }
        }
        '''
        ast, messages = parse(source)
        self.assertIsNotNone(ast)
        self.assertFalse(any(m.level == "error" for m in messages))

    def test_if_with_numeric_comparison_true_branch(self) -> None:
        source = '''
        piste "Cond" {
          threshold = 2
          mélodie instrument: piano {
            mesure 1 {
              si threshold > 1 {
                note(La3, noire)
              } sinon {
                note(Do4, noire)
              }
            }
          }
        }
        '''
        ast, messages = parse(source)
        self.assertIsNotNone(ast)
        self.assertFalse(any(m.level == "error" for m in messages))
        assert ast is not None

        melody = ast.tracks[0].layers[0]
        stmt = melody.measures[0].statements[0]
        self.assertIsInstance(stmt, NoteNode)
        self.assertEqual(stmt.pitch, "La3")

    def test_if_with_numeric_comparison_false_branch(self) -> None:
        source = '''
        piste "Cond" {
          threshold = 0
          mélodie instrument: piano {
            mesure 1 {
              si threshold > 1 {
                note(La3, noire)
              } sinon {
                note(Do4, noire)
              }
            }
          }
        }
        '''
        ast, messages = parse(source)
        self.assertIsNotNone(ast)
        self.assertFalse(any(m.level == "error" for m in messages))
        assert ast is not None

        melody = ast.tracks[0].layers[0]
        stmt = melody.measures[0].statements[0]
        self.assertIsInstance(stmt, NoteNode)
        self.assertEqual(stmt.pitch, "Do4")

    def test_undefined_variable_reports_error(self) -> None:
        source = '''
        piste "Err" {
          batterie {
            mesure {
              kick: [X . . .]
            }
            effets { volume: missing_var + 0.2 }
          }
        }
        '''
        ast, messages = parse(source)
        self.assertIsNotNone(ast)
        self.assertTrue(any(m.level == "error" for m in messages))


if __name__ == "__main__":
    unittest.main()
