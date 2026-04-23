"""
lexer.py
Mouzikti lexical analyser — built with PLY lex.
Converts raw .mzt source text into a flat token stream.
"""

import ply.lex as lex
from compiler.ast_nodes import CompilerMessage

# ---------------------------------------------------------------------------
# Reserved keywords
# ---------------------------------------------------------------------------

RESERVED: dict[str, str] = {
    "piste":       "PISTE",
    "batterie":    "BATTERIE",
    "mélodie":     "MELODIE",
    "melodie":     "MELODIE",
    "basse":       "BASSE",
    "mesure":      "MESURE",
    "note":        "NOTE",
    "accord":      "ACCORD",
    "tempo":       "TEMPO",
    "tonalité":    "TONALITE",
    "tonalite":    "TONALITE",
    "durée":       "DUREE",
    "duree":       "DUREE",
    "instrument":  "INSTRUMENT",
    "effets":      "EFFETS",
    "répéter":     "REPETER",
    "repeter":     "REPETER",
    "si":          "SI",
    "sinon":       "SINON",
    "suivre":      "SUIVRE",
    "racine":      "RACINE",
    "rythme":      "RYTHME",
    "volume":      "VOLUME",
    "reverb":      "REVERB",
    "swing":       "SWING",
    "echo":        "ECHO",
    "oui":         "OUI",
    "non":         "NON",
}

# ---------------------------------------------------------------------------
# Token list
# ---------------------------------------------------------------------------

tokens: tuple = (
    # Literals
    "NUMBER",
    "FLOAT",
    "STRING",
    "NOTE_NAME",
    "CHORD_NAME",
    "IDENTIFIER",

    # Units
    "BPM",
    "MESURES",

    # Beat pattern
    "BEAT_X",
    "BEAT_DOT",

    # Delimiters
    "LBRACE",
    "RBRACE",
    "LBRACKET",
    "RBRACKET",
    "LPAREN",
    "RPAREN",
    "COLON",
    "COMMA",
    "EQUALS",
    "EQEQ",
    "NEQ",
    "GT",
    "GTE",
    "LT",
    "LTE",
    "DOTDOT",
    "PLUS",
    "MINUS",
    "TIMES",

    # Duration keywords (returned as DURATION token with value)
    "DURATION",
) + tuple(RESERVED.values())

# Deduplicate (RESERVED values may repeat)
tokens = tuple(dict.fromkeys(tokens))

# ---------------------------------------------------------------------------
# Simple single-character tokens
# ---------------------------------------------------------------------------

t_LBRACE   = r'\{'
t_RBRACE   = r'\}'
t_LBRACKET = r'\['
t_RBRACKET = r'\]'
t_LPAREN   = r'\('
t_RPAREN   = r'\)'
t_COLON    = r':'
t_COMMA    = r','
t_EQEQ     = r'=='
t_NEQ      = r'!='
t_GTE      = r'>='
t_LTE      = r'<='
t_EQUALS   = r'='
t_GT       = r'>'
t_LT       = r'<'
t_PLUS     = r'\+'
t_MINUS    = r'-'
t_TIMES    = r'\*'

# Whitespace (ignored)
t_ignore = ' \t'

# ---------------------------------------------------------------------------
# Complex token rules (order matters — longer rules first)
# ---------------------------------------------------------------------------

def t_COMMENT(t: lex.LexToken) -> None:
    r'//[^\n]*'
    # Discard comment, do not return a token


def t_DOTDOT(t: lex.LexToken) -> lex.LexToken:
    r'\.\.'
    return t


def t_newline(t: lex.LexToken) -> None:
    r'\n+'
    t.lexer.lineno += len(t.value)


def t_BPM(t: lex.LexToken) -> lex.LexToken:
    r'\d+bpm'
    t.value = int(t.value[:-3])
    return t


def t_MESURES(t: lex.LexToken) -> lex.LexToken:
    r'\d+_mesures'
    t.value = int(t.value.split('_')[0])
    return t


def t_FLOAT(t: lex.LexToken) -> lex.LexToken:
    r'\d+\.\d+'
    t.value = float(t.value)
    return t


def t_NUMBER(t: lex.LexToken) -> lex.LexToken:
    r'\d+'
    t.value = int(t.value)
    return t


def t_STRING(t: lex.LexToken) -> lex.LexToken:
    r'"[^"]*"'
    t.value = t.value[1:-1]   # strip quotes
    return t


# Duration keywords — must come before IDENTIFIER/NOTE_NAME
_DURATIONS = {"ronde", "blanche", "noire", "croche", "double_croche"}

def t_DURATION(t: lex.LexToken) -> lex.LexToken:
    r'double_croche|ronde|blanche|noire|croche'
    return t


# Note names: capitalised solfège + optional accidental + digit
# e.g. La3, Do4, Sol#3, Réb4
def t_NOTE_NAME(t: lex.LexToken) -> lex.LexToken:
    r'(?:Do|Ré|Re|Mi|Fa|Sol|La|Si)[#b]?[0-9]'
    return t


# Chord names: capitalised solfège + _ + quality
# e.g. La_mineur, Do_majeur
def t_CHORD_NAME(t: lex.LexToken) -> lex.LexToken:
    r'(?:Do|Ré|Re|Mi|Fa|Sol|La|Si)[b#]?_(?:majeur|mineur)'
    return t


# Beat pattern X must be checked before IDENTIFIER
def t_BEAT_X(t: lex.LexToken) -> lex.LexToken:
    r'X(?=\s|\.|\])'
    return t


# General identifier / keyword — catches everything else
def t_IDENTIFIER(t: lex.LexToken) -> lex.LexToken:
    r'[A-Za-zÀ-ÿ_][A-Za-zÀ-ÿ0-9_#]*'
    t.type = RESERVED.get(t.value, "IDENTIFIER")
    return t


# Standalone dot (beat rest) — after DOTDOT rule
def t_BEAT_DOT(t: lex.LexToken) -> lex.LexToken:
    r'\.'
    return t


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def t_error(t: lex.LexToken) -> None:
    col = _find_column(t.lexer.lexdata, t)
    print(f"[LEX ERROR] Illegal character '{t.value[0]}' "
          f"at line {t.lineno}, col {col}")
    t.lexer.skip(1)


def _find_column(source: str, token: lex.LexToken) -> int:
    """Calculate the column number of a token."""
    line_start = source.rfind('\n', 0, token.lexpos) + 1
    return token.lexpos - line_start + 1


# ---------------------------------------------------------------------------
# Build & public API
# ---------------------------------------------------------------------------

_lexer = lex.lex()


def tokenize(source: str) -> list[lex.LexToken]:
    """Tokenise a Mouzikti source string.

    Args:
        source: Raw .mzt source code.

    Returns:
        List of PLY LexToken objects.
    """
    _lexer.input(source)
    _lexer.lineno = 1
    tokens_out = []
    while True:
        tok = _lexer.token()
        if tok is None:
            break
        tokens_out.append(tok)
    return tokens_out


def get_lexer() -> lex.Lexer:
    """Return a fresh clone of the lexer for the parser."""
    return _lexer.clone()