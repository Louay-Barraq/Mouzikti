"""
music_theory.py
Pure data module for Mouzikti — scales, note maps, instrument maps.
No side effects, no imports from other project modules.
"""

# ---------------------------------------------------------------------------
# Note name → MIDI number
# Formula: MIDI = (octave + 1) * 12 + semitone_offset
# ---------------------------------------------------------------------------

SOLFEGE_SEMITONES: dict[str, int] = {
    "Do":  0,
    "Ré":  2,  "Re": 2,
    "Mi":  4,
    "Fa":  5,
    "Sol": 7,
    "La":  9,
    "Si":  11,
}

# Accidentals
ACCIDENTAL_OFFSET: dict[str, int] = {
    "#": 1,
    "b": -1,
    "":  0,
}


def solfege_to_midi(note_str: str) -> int:
    """Convert a solfège note string to a MIDI note number.

    Args:
        note_str: Note in format 'La3', 'Do4', 'Sol#3', 'Réb4' etc.

    Returns:
        MIDI note number (0–127).

    Raises:
        ValueError: If note_str is not a recognised note name.

    Examples:
        >>> solfege_to_midi("La3")
        57
        >>> solfege_to_midi("Do4")
        60
    """
    import re
    match = re.fullmatch(r'(Do|Ré|Re|Mi|Fa|Sol|La|Si)([#b]?)(\d)', note_str.strip())
    if not match:
        raise ValueError(f"Unrecognised note format: '{note_str}'")

    name_raw, accidental, octave_str = match.groups()
    name = name_raw

    if name not in SOLFEGE_SEMITONES and name.capitalize() not in SOLFEGE_SEMITONES:
        raise ValueError(f"Unknown note name: '{name_raw}'")

    semitone = SOLFEGE_SEMITONES.get(name, SOLFEGE_SEMITONES.get(name.capitalize(), 0))
    semitone += ACCIDENTAL_OFFSET.get(accidental, 0)
    octave = int(octave_str)
    midi = (octave + 1) * 12 + semitone

    if not 0 <= midi <= 127:
        raise ValueError(f"MIDI note {midi} out of range for '{note_str}'")
    return midi


# Pre-built lookup table (name string → MIDI)
NOTE_MAP: dict[str, int] = {}
for _oct in range(0, 8):
    for _name, _semi in SOLFEGE_SEMITONES.items():
        _midi = (_oct + 1) * 12 + _semi
        if 0 <= _midi <= 127:
            NOTE_MAP[f"{_name}{_oct}"] = _midi

# ---------------------------------------------------------------------------
# Duration name → beats (quarter note = 1 beat)
# ---------------------------------------------------------------------------

DURATION_MAP: dict[str, float] = {
    "ronde":          4.0,
    "blanche":        2.0,
    "noire":          1.0,
    "croche":         0.5,
    "double_croche":  0.25,
    "triple_croche":  0.125,
    "blanche_pointée": 3.0,
    "noire_pointée":   1.5,
    "croche_pointée":  0.75,
}

# ---------------------------------------------------------------------------
# Instrument name → General MIDI program number (0-indexed)
# ---------------------------------------------------------------------------

INSTRUMENT_MAP: dict[str, int] = {
    "piano":              0,
    "guitare":            25,
    "basse_électrique":   33,
    "basse_electrique":   33,
    "violon":             40,
    "flûte":              73,
    "flute":              73,
    "orgue":              19,
    "synthé":             81,
    "synthe":             81,
}

# ---------------------------------------------------------------------------
# Drum voice → General MIDI percussion note (channel 9)
# ---------------------------------------------------------------------------

DRUM_CHANNEL: int = 9

DRUM_MAP: dict[str, int] = {
    "kick":   36,
    "snare":  38,
    "hihat":  42,
    "clap":   39,
    "tom":    45,
    "crash":  49,
}

# ---------------------------------------------------------------------------
# Scales — name → list of allowed base note names (no octave)
# ---------------------------------------------------------------------------

SCALES: dict[str, list[str]] = {
    "Do majeur":   ["Do", "Ré", "Mi", "Fa", "Sol", "La", "Si"],
    "Do mineur":   ["Do", "Ré", "Mib", "Fa", "Sol", "Lab", "Sib"],
    "Sol majeur":  ["Sol", "La", "Si", "Do", "Ré", "Mi", "Fa#"],
    "Ré majeur":   ["Ré", "Mi", "Fa#", "Sol", "La", "Si", "Do#"],
    "Ré mineur":   ["Ré", "Mi", "Fa", "Sol", "La", "Sib", "Do"],
    "La majeur":   ["La", "Si", "Do#", "Ré", "Mi", "Fa#", "Sol#"],
    "La mineur":   ["La", "Si", "Do", "Ré", "Mi", "Fa", "Sol"],
    "Mi majeur":   ["Mi", "Fa#", "Sol#", "La", "Si", "Do#", "Ré#"],
    "Mi mineur":   ["Mi", "Fa#", "Sol", "La", "Si", "Do", "Ré"],
    "Fa majeur":   ["Fa", "Sol", "La", "Sib", "Do", "Ré", "Mi"],
    "Si majeur":   ["Si", "Do#", "Ré#", "Mi", "Fa#", "Sol#", "La#"],
    "Pentatonique": ["Do", "Ré", "Mi", "Sol", "La"],
    "Blues":        ["Do", "Mib", "Fa", "Fa#", "Sol", "Sib"],
}

# ---------------------------------------------------------------------------
# Chords — name → list of solfège base note names
# ---------------------------------------------------------------------------

CHORD_NOTES: dict[str, list[str]] = {
    "Do_majeur":    ["Do", "Mi", "Sol"],
    "Do_mineur":    ["Do", "Mib", "Sol"],
    "Ré_majeur":    ["Ré", "Fa#", "La"],
    "Ré_mineur":    ["Ré", "Fa", "La"],
    "Mi_majeur":    ["Mi", "Sol#", "Si"],
    "Mi_mineur":    ["Mi", "Sol", "Si"],
    "Fa_majeur":    ["Fa", "La", "Do"],
    "Fa_mineur":    ["Fa", "Lab", "Do"],
    "Sol_majeur":   ["Sol", "Si", "Ré"],
    "Sol_mineur":   ["Sol", "Sib", "Ré"],
    "La_majeur":    ["La", "Do#", "Mi"],
    "La_mineur":    ["La", "Do", "Mi"],
    "Si_majeur":    ["Si", "Ré#", "Fa#"],
    "Si_mineur":    ["Si", "Ré", "Fa#"],
}

# Chords that belong to each key (for compatibility checking)
KEY_CHORDS: dict[str, list[str]] = {
    "La mineur":  ["La_mineur", "Ré_mineur", "Mi_mineur", "Do_majeur", "Fa_majeur", "Sol_majeur", "Mi_majeur"],
    "Do majeur":  ["Do_majeur", "Ré_mineur", "Mi_mineur", "Fa_majeur", "Sol_majeur", "La_mineur", "Si_mineur"],
    "Sol majeur": ["Sol_majeur", "La_mineur", "Si_mineur", "Do_majeur", "Ré_majeur", "Mi_mineur", "Fa#_mineur"],
    "Ré majeur":  ["Ré_majeur", "Mi_mineur", "Fa#_mineur", "Sol_majeur", "La_majeur", "Si_mineur", "Do#_mineur"],
    "Ré mineur":  ["Ré_mineur", "Mi_mineur", "Fa_majeur", "Sol_majeur", "La_mineur", "Sib_majeur", "Do_majeur"],
    "Fa majeur":  ["Fa_majeur", "Sol_mineur", "La_mineur", "Sib_majeur", "Do_majeur", "Ré_mineur", "Mi_mineur"],
    "La majeur":  ["La_majeur", "Si_mineur", "Do#_mineur", "Ré_majeur", "Mi_majeur", "Fa#_mineur", "Sol#_mineur"],
    "Mi majeur":  ["Mi_majeur", "Fa#_mineur", "Sol#_mineur", "La_majeur", "Si_majeur", "Do#_mineur", "Ré#_mineur"],
}

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def note_in_scale(note_str: str, scale_name: str) -> bool:
    """Check whether a note belongs to the given scale.

    Args:
        note_str: Note with octave e.g. 'La3', 'Sol#4'.
        scale_name: Scale name e.g. 'La mineur'.

    Returns:
        True if the base note name is in the scale, False otherwise.
        Returns True if scale_name is not recognised (permissive fallback).
    """
    if scale_name not in SCALES:
        return True  # unknown scale — don't reject

    # Strip octave digit and accidental for base name extraction
    import re
    match = re.match(r'([A-ZÉa-zé]+[#b]?)', note_str.strip())
    if not match:
        return False
    base = match.group(1)
    return base in SCALES[scale_name]


def chord_compatible_with_key(chord_name: str, key: str) -> bool:
    """Check whether a chord is compatible with the given key.

    Args:
        chord_name: Chord name e.g. 'La_mineur'.
        key: Key name e.g. 'La mineur'.

    Returns:
        True if compatible or key not recognised, False otherwise.
    """
    if key not in KEY_CHORDS:
        return True
    return chord_name in KEY_CHORDS[key]


def get_chord_midi_notes(chord_name: str, octave: int = 3) -> list[int]:
    """Return MIDI note numbers for a given chord.

    Args:
        chord_name: Chord name e.g. 'La_mineur'.
        octave: Base octave for the chord (default 3).

    Returns:
        List of MIDI note numbers.
    """
    if chord_name not in CHORD_NOTES:
        return []
    notes = []
    for base_note in CHORD_NOTES[chord_name]:
        try:
            notes.append(solfege_to_midi(f"{base_note}{octave}"))
        except ValueError:
            pass
    return notes


def get_chord_root_midi(chord_name: str, octave: int = 2) -> int:
    """Return the MIDI note number for the root of a given chord.

    Args:
        chord_name: Chord name e.g. 'La_mineur'.
        octave: Octave for the root (default 2 for bass).

    Returns:
        MIDI note number for the root note.
    """
    if chord_name not in CHORD_NOTES:
        return 0
    # The first note in CHORD_NOTES is the root
    root_name = CHORD_NOTES[chord_name][0]
    try:
        return solfege_to_midi(f"{root_name}{octave}")
    except ValueError:
        return 0