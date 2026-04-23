"""
semantic.py
Mouzikti semantic analyser — walks the AST and validates music logic.
Collects all errors and warnings without stopping at the first one.
"""

from compiler.ast_nodes import (
    ProgramNode, TrackNode, BatteryNode, MelodyNode,
    MeasureNode, BassNode, NoteNode, AccordNode,
    RepeatNode, EffectsNode, CompilerMessage,
)
from compiler.music_theory import (
    NOTE_MAP, INSTRUMENT_MAP, DRUM_MAP, SCALES,
    DURATION_MAP, note_in_scale, chord_compatible_with_key,
)

# ---------------------------------------------------------------------------
# Semantic Analyser
# ---------------------------------------------------------------------------

class SemanticAnalyzer:
    """Visitor-pattern semantic analyser for the Mouzikti AST."""

    def __init__(self) -> None:
        self.messages: list[CompilerMessage] = []
        self._current_key: str = ""
        self._current_tempo: int = 120

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def analyze(self, program: ProgramNode) -> list[CompilerMessage]:
        """Run semantic analysis on the full program.

        Args:
            program: Root AST node.

        Returns:
            List of CompilerMessage objects (errors and warnings).
        """
        self.messages = []
        for track in program.tracks:
            self._visit_track(track)
        return self.messages

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _error(self, message: str, line: int, suggestion: str = "") -> None:
        self.messages.append(CompilerMessage(
            level="error", message=message, line=line, suggestion=suggestion
        ))

    def _warning(self, message: str, line: int, suggestion: str = "") -> None:
        self.messages.append(CompilerMessage(
            level="warning", message=message, line=line, suggestion=suggestion
        ))

    def _ok(self, message: str) -> None:
        self.messages.append(CompilerMessage(level="ok", message=message))

    # ------------------------------------------------------------------
    # Track
    # ------------------------------------------------------------------

    def _visit_track(self, track: TrackNode) -> None:
        self._current_key = track.key
        self._current_tempo = track.tempo

        # Tempo range
        if track.tempo < 20:
            self._error(
                f"Tempo {track.tempo}bpm is too slow (minimum: 20bpm)",
                track.line,
                "Set tempo to at least 20bpm",
            )
        elif track.tempo > 300:
            self._warning(
                f"Tempo {track.tempo}bpm is unusually high",
                track.line,
                "Consider staying below 300bpm for realistic playback",
            )

        # Key recognition
        if track.key and track.key not in SCALES:
            self._warning(
                f"Key '{track.key}' is not in the known scale list — "
                "note validation will be skipped",
                track.line,
                f"Known keys: {', '.join(SCALES.keys())}",
            )

        # Duration sanity
        if track.duration <= 0:
            self._error(
                f"Track duration must be at least 1 mesure (got {track.duration})",
                track.line,
            )

        # Validate layers
        battery_cycle_beats: list[float] = []
        battery_total_beats: list[float] = []
        melody_total_beats: list[float] = []

        for layer in track.layers:
            if isinstance(layer, BatteryNode):
                cycle_beats, total_beats = self._visit_battery(layer)
                battery_cycle_beats.append(cycle_beats)
                battery_total_beats.append(total_beats)
            elif isinstance(layer, MelodyNode):
                melody_total_beats.append(self._visit_melody(layer))
            elif isinstance(layer, BassNode):
                self._visit_bass(layer)

        # Cross-layer duration mismatch warning (compare total musical length in beats)
        if battery_total_beats and melody_total_beats:
            battery_beats = battery_total_beats[0]
            melody_beats = melody_total_beats[0]
            if abs(battery_beats - melody_beats) > 0.01:
                cycle_hint = ""
                if battery_cycle_beats and battery_cycle_beats[0] > 0:
                    cycle_hint = (
                        f" One drum cycle is {battery_cycle_beats[0]:.2f} beats"
                        f" repeated to {battery_beats:.2f} beats."
                    )
                self._warning(
                    f"Drum layer spans {battery_beats:.2f} beats but melody spans "
                    f"{melody_beats:.2f} beats — lengths differ.{cycle_hint}",
                    track.line,
                    "Align your beat and melody lengths for clean looping",
                )

    # ------------------------------------------------------------------
    # Battery
    # ------------------------------------------------------------------

    def _visit_battery(self, battery: BatteryNode) -> tuple[float, float]:
        """Validate battery block and return (cycle_beats, total_beats)."""
        if battery.repeat < 1:
            self._error(
                "répéter count must be ≥ 1",
                battery.line,
                "Change to: répéter 1 (or higher)",
            )

        step_counts: list[int] = []

        for pattern in battery.patterns:
            if pattern.voice not in DRUM_MAP:
                self._error(
                    f"Unknown drum voice '{pattern.voice}'",
                    pattern.line,
                    f"Available voices: {', '.join(DRUM_MAP.keys())}",
                )
            step_counts.append(len(pattern.steps))

        # All voices must have same step count
        if step_counts and len(set(step_counts)) > 1:
            self._error(
                f"Drum patterns have inconsistent lengths: {step_counts} — "
                "all voices must have the same number of steps",
                battery.line,
                "Make all beat rows the same length (e.g. all 16 steps)",
            )

        self._visit_effects(battery.effects)
        if not step_counts:
            return 0.0, 0.0

        # Codegen timing: each drum step is emitted as 0.5 beat.
        cycle_beats = step_counts[0] * 0.5
        total_beats = cycle_beats * battery.repeat
        return cycle_beats, total_beats

    # ------------------------------------------------------------------
    # Melody
    # ------------------------------------------------------------------

    def _visit_melody(self, melody: MelodyNode) -> float:
        """Validate melody block. Returns total duration in beats."""
        if melody.instrument not in INSTRUMENT_MAP:
            self._error(
                f"Unknown instrument '{melody.instrument}'",
                melody.line,
                f"Available instruments: {', '.join(INSTRUMENT_MAP.keys())}",
            )

        total_beats = 0.0
        for measure in melody.measures:
            total_beats += self._visit_measure(measure)

        self._visit_effects(melody.effects)
        return total_beats

    def _visit_measure(self, measure: MeasureNode) -> float:
        """Validate a measure range block. Returns duration in beats."""
        if measure.start > measure.end:
            self._error(
                f"Measure range {measure.start}..{measure.end} is invalid "
                "(start must be ≤ end)",
                measure.line,
            )
        beats_per_measure = 0.0
        for stmt in measure.statements:
            if isinstance(stmt, NoteNode):
                self._visit_note(stmt)
                beats_per_measure += DURATION_MAP.get(stmt.duration, 1.0)
            elif isinstance(stmt, AccordNode):
                self._visit_accord(stmt)
                beats_per_measure += DURATION_MAP.get(stmt.duration, 2.0)
            elif isinstance(stmt, RepeatNode):
                beats_per_measure += self._visit_repeat(stmt)

        measure_span = max(measure.end - measure.start + 1, 0)
        return beats_per_measure * measure_span

    # ------------------------------------------------------------------
    # Note & Chord
    # ------------------------------------------------------------------

    def _visit_note(self, note: NoteNode) -> None:
        # Note name recognised
        if note.pitch not in NOTE_MAP:
            self._error(
                f"Unknown note '{note.pitch}'",
                note.line,
                "Use solfège names like La3, Do4, Mi4",
            )
        else:
            # Note in scale
            if self._current_key and not note_in_scale(note.pitch, self._current_key):
                self._error(
                    f"Note '{note.pitch}' is not in scale '{self._current_key}'",
                    note.line,
                    f"Notes allowed in {self._current_key}: "
                    f"{', '.join(SCALES.get(self._current_key, []))}",
                )

        # Duration recognised
        if note.duration not in DURATION_MAP:
            self._error(
                f"Unknown duration '{note.duration}'",
                note.line,
                f"Available: {', '.join(DURATION_MAP.keys())}",
            )

    def _visit_accord(self, accord: AccordNode) -> None:
        # Duration check
        if accord.duration not in DURATION_MAP:
            self._error(
                f"Unknown duration '{accord.duration}' in accord",
                accord.line,
                f"Available: {', '.join(DURATION_MAP.keys())}",
            )
        # Key compatibility
        if self._current_key and not chord_compatible_with_key(accord.name, self._current_key):
            self._warning(
                f"Chord '{accord.name}' may not be in key '{self._current_key}'",
                accord.line,
                "This is a warning — it may still sound fine as a passing chord",
            )

    # ------------------------------------------------------------------
    # Bass
    # ------------------------------------------------------------------

    def _visit_bass(self, bass: BassNode) -> None:
        if bass.instrument not in INSTRUMENT_MAP:
            self._error(
                f"Unknown bass instrument '{bass.instrument}'",
                bass.line,
                f"Available: {', '.join(INSTRUMENT_MAP.keys())}",
            )

    # ------------------------------------------------------------------
    # Repeat
    # ------------------------------------------------------------------

    def _visit_repeat(self, repeat: RepeatNode) -> float:
        if repeat.count < 1:
            self._error(
                "répéter count must be ≥ 1",
                repeat.line,
                "Use a positive integer",
            )
        body_beats = 0.0
        for stmt in repeat.body:
            if isinstance(stmt, NoteNode):
                self._visit_note(stmt)
                body_beats += DURATION_MAP.get(stmt.duration, 1.0)
            elif isinstance(stmt, AccordNode):
                self._visit_accord(stmt)
                body_beats += DURATION_MAP.get(stmt.duration, 2.0)
        return body_beats * max(repeat.count, 0)

    # ------------------------------------------------------------------
    # Effects
    # ------------------------------------------------------------------

    def _visit_effects(self, fx: EffectsNode) -> None:
        if not (0.0 <= fx.volume <= 1.0):
            self._error(
                f"Volume {fx.volume} is out of range — must be between 0.0 and 1.0",
                fx.line,
                "Set volume to a value like 0.8",
            )
        if not (0.0 <= fx.reverb <= 1.0):
            self._error(
                f"Reverb {fx.reverb} is out of range — must be between 0.0 and 1.0",
                fx.line,
            )
        if not (0.0 <= fx.swing <= 1.0):
            self._error(
                f"Swing {fx.swing} is out of range — must be between 0.0 and 1.0",
                fx.line,
            )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze(program: ProgramNode) -> list[CompilerMessage]:
    """Run semantic analysis on a parsed program.

    Args:
        program: Root ProgramNode from the parser.

    Returns:
        List of CompilerMessage (errors and warnings). Empty = clean.
    """
    analyser = SemanticAnalyzer()
    messages = analyser.analyze(program)

    error_count   = sum(1 for m in messages if m.level == "error")
    warning_count = sum(1 for m in messages if m.level == "warning")

    if error_count == 0 and warning_count == 0:
        messages.append(CompilerMessage(
            level="ok",
            message="Semantic analysis passed — no errors or warnings",
        ))
    return messages