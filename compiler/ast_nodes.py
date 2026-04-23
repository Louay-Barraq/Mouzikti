"""
ast_nodes.py
Dataclass definitions for every node in the Mouzikti AST.
No business logic — pure data containers only.
"""

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Compiler messages
# ---------------------------------------------------------------------------

@dataclass
class CompilerMessage:
    """A diagnostic message produced by any compiler stage."""
    level: str          # "error" | "warning" | "info" | "ok"
    message: str
    line: int = 0
    suggestion: str = ""

    def __str__(self) -> str:
        icon = {"error": "✗", "warning": "⚠", "info": "→", "ok": "✓"}.get(self.level, "·")
        loc = f" line {self.line}" if self.line else ""
        sug = f"\n    → {self.suggestion}" if self.suggestion else ""
        return f"{icon} [{self.level.upper()}]{loc} — {self.message}{sug}"


# ---------------------------------------------------------------------------
# Effects
# ---------------------------------------------------------------------------

@dataclass
class EffectsNode:
    """Audio effects applied to a layer (reverb, echo, volume, swing)."""
    reverb: float = 0.0
    echo: float = 0.0
    volume: float = 1.0
    swing: float = 0.0
    line: int = 0


# ---------------------------------------------------------------------------
# Beat / Rhythm nodes
# ---------------------------------------------------------------------------

@dataclass
class BeatPatternNode:
    """A single drum voice pattern as a list of steps ('X' or '.')."""
    voice: str              # e.g. "kick", "snare", "hihat"
    steps: list[str]        # e.g. ['X','.','.','.','X',...]
    line: int = 0


@dataclass
class BatteryNode:
    """The full drum/battery block inside a track."""
    patterns: list[BeatPatternNode] = field(default_factory=list)
    effects: EffectsNode = field(default_factory=EffectsNode)
    repeat: int = 1
    line: int = 0


# ---------------------------------------------------------------------------
# Melody nodes
# ---------------------------------------------------------------------------

@dataclass
class NoteNode:
    """A single note event."""
    pitch: str          # e.g. "La3"
    duration: str       # e.g. "noire"
    line: int = 0

    def __repr__(self) -> str:
        return f"Note({self.pitch}, {self.duration})"


@dataclass
class AccordNode:
    """A chord event (multiple simultaneous notes)."""
    name: str           # e.g. "La_mineur"
    duration: str       # e.g. "blanche"
    line: int = 0

    def __repr__(self) -> str:
        return f"Accord({self.name}, {self.duration})"


@dataclass
class RepeatNode:
    """A repeat block containing a list of statements."""
    count: int
    body: list = field(default_factory=list)
    line: int = 0


@dataclass
class MeasureNode:
    """A measure range (mesure 1..4) containing note/chord statements."""
    start: int
    end: int
    statements: list = field(default_factory=list)   # NoteNode | AccordNode | RepeatNode
    line: int = 0


@dataclass
class MelodyNode:
    """A melodic layer (mélodie) inside a track."""
    instrument: str
    measures: list[MeasureNode] = field(default_factory=list)
    effects: EffectsNode = field(default_factory=EffectsNode)
    line: int = 0


# ---------------------------------------------------------------------------
# Bass node
# ---------------------------------------------------------------------------

@dataclass
class BassNode:
    """A bass layer inside a track."""
    instrument: str = "basse_électrique"
    follow_chord: bool = True
    rhythm: list[str] = field(default_factory=list)   # step pattern
    effects: EffectsNode = field(default_factory=EffectsNode)
    line: int = 0


# ---------------------------------------------------------------------------
# Variable assignment
# ---------------------------------------------------------------------------

@dataclass
class VariableNode:
    """A variable assignment statement."""
    name: str
    value: object       # int | float | str
    line: int = 0


# ---------------------------------------------------------------------------
# Top-level nodes
# ---------------------------------------------------------------------------

@dataclass
class TrackNode:
    """A single piste (track) — top-level container."""
    name: str
    tempo: int = 120
    key: str = ""
    duration: int = 8           # in mesures
    layers: list = field(default_factory=list)   # BatteryNode | MelodyNode | BassNode
    line: int = 0

    def __repr__(self) -> str:
        return f"Track('{self.name}', {self.tempo}bpm, key='{self.key}', layers={len(self.layers)})"


@dataclass
class ProgramNode:
    """The root of the AST — contains all tracks in the source file."""
    tracks: list[TrackNode] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"Program({len(self.tracks)} track(s))"


# ---------------------------------------------------------------------------
# Pretty printer
# ---------------------------------------------------------------------------

def pretty_print(node: object, indent: int = 0) -> None:
    """Recursively print an AST node tree for debugging."""
    pad = "  " * indent
    name = type(node).__name__

    if isinstance(node, ProgramNode):
        print(f"{pad}Program ({len(node.tracks)} track(s))")
        for t in node.tracks:
            pretty_print(t, indent + 1)

    elif isinstance(node, TrackNode):
        print(f"{pad}Track: '{node.name}' | {node.tempo}bpm | key='{node.key}' | {node.duration} mesures")
        for layer in node.layers:
            pretty_print(layer, indent + 1)

    elif isinstance(node, BatteryNode):
        print(f"{pad}Battery (repeat={node.repeat})")
        for p in node.patterns:
            print(f"{pad}  {p.voice}: {''.join(p.steps)}")

    elif isinstance(node, MelodyNode):
        print(f"{pad}Melody (instrument={node.instrument})")
        for m in node.measures:
            pretty_print(m, indent + 1)

    elif isinstance(node, MeasureNode):
        print(f"{pad}Measure {node.start}..{node.end} ({len(node.statements)} stmt(s))")
        for s in node.statements:
            pretty_print(s, indent + 1)

    elif isinstance(node, BassNode):
        rhy = ''.join(node.rhythm) if node.rhythm else "follow chord"
        print(f"{pad}Bass (instrument={node.instrument}, rhythm={rhy})")

    elif isinstance(node, NoteNode):
        print(f"{pad}Note({node.pitch}, {node.duration})")

    elif isinstance(node, AccordNode):
        print(f"{pad}Accord({node.name}, {node.duration})")

    elif isinstance(node, RepeatNode):
        print(f"{pad}Repeat x{node.count}")
        for s in node.body:
            pretty_print(s, indent + 1)

    elif isinstance(node, EffectsNode):
        print(f"{pad}Effects(vol={node.volume}, reverb={node.reverb}, swing={node.swing})")

    else:
        print(f"{pad}{name}: {node}")