"""
parser.py
Mouzikti LALR parser — built with PLY yacc.
Validates grammar and constructs the AST from the token stream.
"""

import ply.yacc as yacc
from compiler.lexer import tokens, get_lexer          # noqa: F401  (PLY needs tokens in scope)
from compiler.ast_nodes import (
    ProgramNode, TrackNode, BatteryNode, BeatPatternNode,
    MelodyNode, MeasureNode, BassNode,
    NoteNode, AccordNode, RepeatNode,
    EffectsNode, CompilerMessage,
)

# ---------------------------------------------------------------------------
# Operator precedence (low → high)
# ---------------------------------------------------------------------------

precedence = (
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES'),
)

# ---------------------------------------------------------------------------
# Program
# ---------------------------------------------------------------------------

def p_program(p):
    '''program : track_list'''
    p[0] = ProgramNode(tracks=p[1])


def p_track_list_multi(p):
    '''track_list : track_list track'''
    p[0] = p[1] + [p[2]]


def p_track_list_single(p):
    '''track_list : track'''
    p[0] = [p[1]]


# ---------------------------------------------------------------------------
# Track
# ---------------------------------------------------------------------------

def p_track(p):
    '''track : PISTE STRING LBRACE track_body RBRACE'''
    attrs, layers = p[4]
    p[0] = TrackNode(
        name=p[2],
        tempo=attrs.get('tempo', 120),
        key=attrs.get('key', ''),
        duration=attrs.get('duration', 8),
        layers=layers,
        line=p.lineno(1),
    )


def p_track_body(p):
    '''track_body : track_attr_list layer_list'''
    p[0] = (p[1], p[2])


def p_track_attr_list_multi(p):
    '''track_attr_list : track_attr_list track_attr'''
    p[0] = {**p[1], **p[2]}


def p_track_attr_list_empty(p):
    '''track_attr_list : empty'''
    p[0] = {}


def p_track_attr_tempo(p):
    '''track_attr : TEMPO COLON BPM'''
    p[0] = {'tempo': p[3]}


def p_track_attr_tonalite(p):
    '''track_attr : TONALITE COLON STRING'''
    p[0] = {'key': p[3]}


def p_track_attr_duree(p):
    '''track_attr : DUREE COLON MESURES'''
    p[0] = {'duration': p[3]}


def p_track_attr_variable_assignment(p):
    '''track_attr : IDENTIFIER EQUALS number_val'''
    _parse_variables[p[1]] = p[3]
    p[0] = {}


# ---------------------------------------------------------------------------
# Layer list
# ---------------------------------------------------------------------------

def p_layer_list_multi(p):
    '''layer_list : layer_list layer'''
    p[0] = p[1] + [p[2]]


def p_layer_list_empty(p):
    '''layer_list : empty'''
    p[0] = []


def p_layer_battery(p):
    '''layer : battery_block'''
    p[0] = p[1]


def p_layer_melody(p):
    '''layer : melody_block'''
    p[0] = p[1]


def p_layer_bass(p):
    '''layer : bass_block'''
    p[0] = p[1]


# ---------------------------------------------------------------------------
# Battery block
# ---------------------------------------------------------------------------

def p_battery_block(p):
    '''battery_block : BATTERIE LBRACE battery_body RBRACE'''
    patterns, effects, repeat = p[3]
    p[0] = BatteryNode(patterns=patterns, effects=effects, repeat=repeat, line=p.lineno(1))


def p_battery_body(p):
    '''battery_body : mesure_block battery_opts'''
    p[0] = (p[1], p[2][0], p[2][1])


def p_mesure_block(p):
    '''mesure_block : MESURE LBRACE beat_row_list RBRACE'''
    p[0] = p[3]


def p_beat_row_list_multi(p):
    '''beat_row_list : beat_row_list beat_row'''
    p[0] = p[1] + [p[2]]


def p_beat_row_list_single(p):
    '''beat_row_list : beat_row'''
    p[0] = [p[1]]


def p_beat_row(p):
    '''beat_row : IDENTIFIER COLON LBRACKET beat_steps RBRACKET'''
    p[0] = BeatPatternNode(voice=p[1], steps=p[4], line=p.lineno(1))


def p_beat_steps_multi(p):
    '''beat_steps : beat_steps beat_step'''
    p[0] = p[1] + [p[2]]


def p_beat_steps_single(p):
    '''beat_steps : beat_step'''
    p[0] = [p[1]]


def p_beat_step_x(p):
    '''beat_step : BEAT_X'''
    p[0] = 'X'


def p_beat_step_dot(p):
    '''beat_step : BEAT_DOT'''
    p[0] = '.'


def p_battery_opts(p):
    '''battery_opts : effects_block repeat_stmt
                    | effects_block
                    | repeat_stmt
                    | empty'''
    if len(p) == 3:
        p[0] = (p[1], p[2])
    elif len(p) == 2 and p[1] is not None:
        if isinstance(p[1], EffectsNode):
            p[0] = (p[1], 1)
        else:
            p[0] = (EffectsNode(), p[1])
    else:
        p[0] = (EffectsNode(), 1)


def p_repeat_stmt(p):
    '''repeat_stmt : REPETER NUMBER'''
    p[0] = p[2]


# ---------------------------------------------------------------------------
# Melody block
# ---------------------------------------------------------------------------

def p_melody_block(p):
    '''melody_block : MELODIE INSTRUMENT COLON IDENTIFIER LBRACE melody_body RBRACE'''
    measures, effects = p[6]
    p[0] = MelodyNode(
        instrument=p[4],
        measures=measures,
        effects=effects,
        line=p.lineno(1),
    )


def p_melody_body(p):
    '''melody_body : measure_list effects_block
                   | measure_list'''
    if len(p) == 3:
        p[0] = (p[1], p[2])
    else:
        p[0] = (p[1], EffectsNode())


def p_measure_list_multi(p):
    '''measure_list : measure_list measure_block'''
    p[0] = p[1] + [p[2]]


def p_measure_list_single(p):
    '''measure_list : measure_block'''
    p[0] = [p[1]]


def p_measure_block_range(p):
    '''measure_block : MESURE NUMBER DOTDOT NUMBER LBRACE stmt_list RBRACE'''
    p[0] = MeasureNode(start=p[2], end=p[4], statements=p[6], line=p.lineno(1))


def p_measure_block_single(p):
    '''measure_block : MESURE NUMBER LBRACE stmt_list RBRACE'''
    p[0] = MeasureNode(start=p[2], end=p[2], statements=p[4], line=p.lineno(1))


def p_stmt_list_multi(p):
    '''stmt_list : stmt_list stmt'''
    if isinstance(p[2], list):
        p[0] = p[1] + p[2]
    else:
        p[0] = p[1] + [p[2]]


def p_stmt_list_empty(p):
    '''stmt_list : empty'''
    p[0] = []


def p_stmt_note(p):
    '''stmt : NOTE LPAREN NOTE_NAME COMMA DURATION RPAREN'''
    p[0] = NoteNode(pitch=p[3], duration=p[5], line=p.lineno(1))


def p_stmt_accord(p):
    '''stmt : ACCORD LPAREN CHORD_NAME COMMA DURATION RPAREN'''
    p[0] = AccordNode(name=p[3], duration=p[5], line=p.lineno(1))


def p_stmt_repeat(p):
    '''stmt : REPETER NUMBER LBRACE stmt_list RBRACE'''
    p[0] = RepeatNode(count=p[2], body=p[4], line=p.lineno(1))


def p_stmt_if(p):
    '''stmt : SI bool_expr LBRACE stmt_list RBRACE'''
    p[0] = p[4] if p[2] else []


def p_stmt_if_else(p):
    '''stmt : SI bool_expr LBRACE stmt_list RBRACE SINON LBRACE stmt_list RBRACE'''
    p[0] = p[4] if p[2] else p[8]


def p_bool_expr_literal(p):
    '''bool_expr : bool_literal'''
    p[0] = p[1]


def p_bool_expr_group(p):
    '''bool_expr : LPAREN bool_expr RPAREN'''
    p[0] = p[2]


def p_bool_expr_number_truthy(p):
    '''bool_expr : number_expr'''
    p[0] = p[1] != 0.0


def p_bool_expr_eq(p):
    '''bool_expr : number_expr EQEQ number_expr'''
    p[0] = p[1] == p[3]


def p_bool_expr_neq(p):
    '''bool_expr : number_expr NEQ number_expr'''
    p[0] = p[1] != p[3]


def p_bool_expr_gt(p):
    '''bool_expr : number_expr GT number_expr'''
    p[0] = p[1] > p[3]


def p_bool_expr_gte(p):
    '''bool_expr : number_expr GTE number_expr'''
    p[0] = p[1] >= p[3]


def p_bool_expr_lt(p):
    '''bool_expr : number_expr LT number_expr'''
    p[0] = p[1] < p[3]


def p_bool_expr_lte(p):
    '''bool_expr : number_expr LTE number_expr'''
    p[0] = p[1] <= p[3]


def p_bool_literal_oui(p):
    '''bool_literal : OUI'''
    p[0] = True


def p_bool_literal_non(p):
    '''bool_literal : NON'''
    p[0] = False


# ---------------------------------------------------------------------------
# Bass block
# ---------------------------------------------------------------------------

def p_bass_block(p):
    '''bass_block : BASSE INSTRUMENT COLON IDENTIFIER LBRACE bass_body RBRACE'''
    follow, rhythm = p[6]
    p[0] = BassNode(
        instrument=p[4],
        follow_chord=follow,
        rhythm=rhythm,
        line=p.lineno(1),
    )


def p_bass_body_follow_rythme(p):
    '''bass_body : SUIVRE IDENTIFIER RACINE COLON OUI RYTHME COLON LBRACKET beat_steps RBRACKET'''
    p[0] = (True, p[9])


def p_bass_body_follow_only(p):
    '''bass_body : SUIVRE IDENTIFIER RACINE COLON OUI'''
    p[0] = (True, [])


def p_bass_body_rythme_only(p):
    '''bass_body : RYTHME COLON LBRACKET beat_steps RBRACKET'''
    p[0] = (False, p[4])


# ---------------------------------------------------------------------------
# Effects block
# ---------------------------------------------------------------------------

def p_effects_block(p):
    '''effects_block : EFFETS LBRACE effect_list RBRACE'''
    fx = EffectsNode(line=p.lineno(1))
    for k, v in p[3]:
        if k == 'reverb':
            fx.reverb = v
        elif k == 'echo':
            fx.echo = v
        elif k == 'volume':
            fx.volume = v
        elif k == 'swing':
            fx.swing = v
    p[0] = fx


def p_effect_list_multi(p):
    '''effect_list : effect_list COMMA effect_item'''
    p[0] = p[1] + [p[3]]


def p_effect_list_single(p):
    '''effect_list : effect_item'''
    p[0] = [p[1]]


def p_effect_item_reverb(p):
    '''effect_item : REVERB COLON number_val'''
    p[0] = ('reverb', p[3])


def p_effect_item_echo(p):
    '''effect_item : ECHO COLON number_val'''
    p[0] = ('echo', p[3])


def p_effect_item_volume(p):
    '''effect_item : VOLUME COLON number_val'''
    p[0] = ('volume', p[3])


def p_effect_item_swing(p):
    '''effect_item : SWING COLON number_val'''
    p[0] = ('swing', p[3])


def p_number_val_float(p):
    '''number_expr : FLOAT'''
    p[0] = p[1]


def p_number_val_int(p):
    '''number_expr : NUMBER'''
    p[0] = float(p[1])


def p_number_val_identifier(p):
    '''number_expr : IDENTIFIER'''
    name = p[1]
    if name in _parse_variables:
        p[0] = _parse_variables[name]
        return

    _parse_errors.append(CompilerMessage(
        level="error",
        message=f"Variable '{name}' is not defined yet — defaulting to 0",
        line=p.lineno(1),
        suggestion="Define the variable earlier in the piste block",
    ))
    p[0] = 0.0


def p_number_expr_group(p):
    '''number_expr : LPAREN number_expr RPAREN'''
    p[0] = p[2]


def p_number_expr_plus(p):
    '''number_expr : number_expr PLUS number_expr'''
    p[0] = p[1] + p[3]


def p_number_expr_minus(p):
    '''number_expr : number_expr MINUS number_expr'''
    p[0] = p[1] - p[3]


def p_number_expr_times(p):
    '''number_expr : number_expr TIMES number_expr'''
    p[0] = p[1] * p[3]


def p_number_val_expr(p):
    '''number_val : number_expr'''
    p[0] = p[1]


# ---------------------------------------------------------------------------
# Empty production
# ---------------------------------------------------------------------------

def p_empty(p):
    '''empty :'''
    p[0] = None


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

_parse_errors: list[CompilerMessage] = []
_parse_variables: dict[str, float] = {}


def p_error(p) -> None:
    global _parse_errors
    if p is None:
        _parse_errors.append(CompilerMessage(
            level="error",
            message="Unexpected end of file — check for unclosed '{' blocks",
            line=0,
        ))
    else:
        _parse_errors.append(CompilerMessage(
            level="error",
            message=f"Unexpected token '{p.value}' ({p.type})",
            line=p.lineno,
            suggestion="Check for missing ':' ',' or mismatched brackets near this line",
        ))


# ---------------------------------------------------------------------------
# Build parser & public API
# ---------------------------------------------------------------------------

_parser = yacc.yacc(debug=False, write_tables=False)


def parse(source: str) -> tuple[ProgramNode | None, list[CompilerMessage]]:
    """Parse Mouzikti source code into an AST.

    Args:
        source: Raw .mzt source code string.

    Returns:
        Tuple of (ProgramNode | None, list[CompilerMessage]).
        ProgramNode is None if parsing failed with errors.
    """
    global _parse_errors, _parse_variables
    _parse_errors = []
    _parse_variables = {}

    lexer = get_lexer()
    lexer.lineno = 1

    result = _parser.parse(source, lexer=lexer, tracking=True)

    messages = list(_parse_errors)
    if result is None and not messages:
        messages.append(CompilerMessage(
            level="error",
            message="Parser returned no result — the source may be empty or entirely invalid",
            line=0,
        ))

    return result, messages