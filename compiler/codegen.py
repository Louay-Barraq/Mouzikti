"""
codegen.py
Mouzikti MIDI code generator — walks the AST and emits MIDI events.
Uses midiutil to write .mid files.
"""

import os
from midiutil import MIDIFile
from compiler.ast_nodes import (
    ProgramNode, TrackNode, BatteryNode, MelodyNode,
    MeasureNode, BassNode, NoteNode, AccordNode,
    RepeatNode, CompilerMessage,
)
from compiler.music_theory import (
    INSTRUMENT_MAP, DRUM_MAP, DRUM_CHANNEL,
    DURATION_MAP, solfege_to_midi, get_chord_midi_notes,
    get_chord_root_midi,
)


class CodegenError(Exception):
    """Raised when MIDI generation fails unrecoverably."""


class MIDIGenerator:
    """Translates an annotated Mouzikti AST into a MIDI file."""

    def __init__(self) -> None:
        self._midi: MIDIFile | None = None
        self._track_index: int = 0
        self._messages: list[CompilerMessage] = []
        self._max_beat: float = 0.0

    # ------------------------------------------------------------------
    # Public entry
    # ------------------------------------------------------------------

    def generate(self, program: ProgramNode, output_path: str) -> tuple[str, float]:
        """Generate a MIDI file from the program AST.

        Args:
            program: Root ProgramNode (must have passed semantic analysis).
            output_path: Destination path for the .mid file.

        Returns:
            Tuple of (absolute_path_to_file, total_duration_seconds).

        Raises:
            CodegenError: If generation fails.
        """
        self._messages = []
        num_tracks = self._count_midi_tracks(program)
        self._midi = MIDIFile(num_tracks, deinterleave=False)
        self._track_index = 0

        for track_node in program.tracks:
            self._process_track(track_node)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            self._midi.writeFile(f)

        self._messages.append(CompilerMessage(
            level="ok",
            message=f"MIDI file written → {output_path}",
        ))
        
        # Calculate duration in seconds based on max beat and first track's tempo
        # (Assuming unified tempo for the whole piece for duration estimation)
        main_tempo = program.tracks[0].tempo if program.tracks else 120
        duration_s = self._max_beat * (60.0 / main_tempo)
        
        return os.path.abspath(output_path), duration_s

    def get_messages(self) -> list[CompilerMessage]:
        """Return diagnostic messages from the last generate() call."""
        return list(self._messages)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _count_midi_tracks(self, program: ProgramNode) -> int:
        """Count total MIDI tracks needed across all pistes."""
        count = 0
        for track in program.tracks:
            for layer in track.layers:
                count += 1
        return max(count, 1)

    def _process_track(self, track: TrackNode) -> None:
        # Pre-scan for chords across all melody layers to build a timeline
        chord_timeline = []  # list of (start_beat, end_beat, chord_name)
        for layer in track.layers:
            if isinstance(layer, MelodyNode):
                beat = 0.0
                for measure in layer.measures:
                    span = max(measure.end - measure.start + 1, 1)
                    for _ in range(span):
                        for stmt in measure.statements:
                            # We only care about chords for the timeline
                            if isinstance(stmt, AccordNode):
                                dur = DURATION_MAP.get(stmt.duration, 2.0)
                                chord_timeline.append((beat, beat + dur, stmt.name))
                                beat += dur
                            elif isinstance(stmt, NoteNode):
                                beat += DURATION_MAP.get(stmt.duration, 1.0)
                            elif isinstance(stmt, RepeatNode):
                                # Simplified: only scan top-level chords in repeats
                                rep_start = beat
                                for _ in range(stmt.count):
                                    for substmt in stmt.body:
                                        if isinstance(substmt, AccordNode):
                                            dur = DURATION_MAP.get(substmt.duration, 2.0)
                                            chord_timeline.append((beat, beat + dur, substmt.name))
                                            beat += dur
                                        elif isinstance(substmt, NoteNode):
                                            beat += DURATION_MAP.get(substmt.duration, 1.0)
                
        for layer in track.layers:
            if isinstance(layer, BatteryNode):
                self._process_battery(layer, track.tempo)
            elif isinstance(layer, MelodyNode):
                self._process_melody(layer, track.tempo)
            elif isinstance(layer, BassNode):
                self._process_bass(layer, track.tempo, chord_timeline)

    # ------------------------------------------------------------------
    # Battery (drums)
    # ------------------------------------------------------------------

    def _process_battery(self, battery: BatteryNode, tempo: int) -> None:
        t = self._track_index
        self._midi.addTempo(t, 0, tempo)
        self._track_index += 1

        num_steps = len(battery.patterns[0].steps) if battery.patterns else 16
        step_duration = 0.5   # each step = one eighth note = 0.5 beats

        for rep in range(battery.repeat):
            time_offset = rep * num_steps * step_duration
            for pattern in battery.patterns:
                midi_note = DRUM_MAP.get(pattern.voice)
                if midi_note is None:
                    continue
                for step_idx, step in enumerate(pattern.steps):
                    if step == 'X':
                        beat_time = time_offset + step_idx * step_duration
                        self._midi.addNote(
                            track=t,
                            channel=DRUM_CHANNEL,
                            pitch=midi_note,
                            time=beat_time,
                            duration=step_duration,
                            volume=int(90 * battery.effects.volume),
                        )
                        self._max_beat = max(self._max_beat, beat_time + step_duration)

    # ------------------------------------------------------------------
    # Melody
    # ------------------------------------------------------------------

    def _process_melody(self, melody: MelodyNode, tempo: int) -> None:
        t = self._track_index
        channel = self._track_index % 8   # channels 0–8 (skip 9 = drums)
        if channel >= DRUM_CHANNEL:
            channel += 1

        self._midi.addTempo(t, 0, tempo)
        program_num = INSTRUMENT_MAP.get(melody.instrument, 0)
        self._midi.addProgramChange(t, channel, 0, program_num)
        self._track_index += 1

        current_beat: float = 0.0
        for measure in melody.measures:
            current_beat = self._process_measure(
                measure, t, channel, current_beat,
                int(90 * melody.effects.volume),
            )

    def _process_measure(
        self,
        measure: MeasureNode,
        track: int,
        channel: int,
        start_beat: float,
        volume: int,
    ) -> float:
        """Process a measure block; returns beat position after last event."""
        beat = start_beat
        measure_span = max(measure.end - measure.start + 1, 1)
        for _ in range(measure_span):
            for stmt in measure.statements:
                beat = self._process_stmt(stmt, track, channel, beat, volume)
        return beat

    def _process_stmt(
        self,
        stmt,
        track: int,
        channel: int,
        beat: float,
        volume: int,
    ) -> float:
        """Dispatch a single statement node; returns updated beat position."""
        if isinstance(stmt, NoteNode):
            return self._process_note(stmt, track, channel, beat, volume)
        elif isinstance(stmt, AccordNode):
            return self._process_accord(stmt, track, channel, beat, volume)
        elif isinstance(stmt, RepeatNode):
            return self._process_repeat_block(stmt, track, channel, beat, volume)
        return beat

    def _process_note(
        self,
        note: NoteNode,
        track: int,
        channel: int,
        beat: float,
        volume: int,
    ) -> float:
        duration = DURATION_MAP.get(note.duration, 1.0)
        try:
            pitch = solfege_to_midi(note.pitch)
        except ValueError:
            self._messages.append(CompilerMessage(
                level="warning",
                message=f"Skipping unresolvable note '{note.pitch}'",
                line=note.line,
            ))
            return beat + duration

        self._midi.addNote(track, channel, pitch, beat, duration, volume)
        self._max_beat = max(self._max_beat, beat + duration)
        return beat + duration

    def _process_accord(
        self,
        accord: AccordNode,
        track: int,
        channel: int,
        beat: float,
        volume: int,
    ) -> float:
        duration = DURATION_MAP.get(accord.duration, 2.0)
        midi_notes = get_chord_midi_notes(accord.name, octave=3)
        if not midi_notes:
            self._messages.append(CompilerMessage(
                level="warning",
                message=f"Chord '{accord.name}' not found — skipping",
                line=accord.line,
            ))
            return beat + duration

        for pitch in midi_notes:
            self._midi.addNote(track, channel, pitch, beat, duration, volume - 10)
        self._max_beat = max(self._max_beat, beat + duration)
        return beat + duration

    def _process_repeat_block(
        self,
        repeat: RepeatNode,
        track: int,
        channel: int,
        beat: float,
        volume: int,
    ) -> float:
        for _ in range(repeat.count):
            for stmt in repeat.body:
                beat = self._process_stmt(stmt, track, channel, beat, volume)
        return beat

    # ------------------------------------------------------------------
    # Bass
    # ------------------------------------------------------------------

    def _process_bass(self, bass: BassNode, tempo: int, chord_timeline: list) -> None:
        t = self._track_index
        channel = self._track_index % 8
        if channel >= DRUM_CHANNEL:
            channel += 1

        self._midi.addTempo(t, 0, tempo)
        program_num = INSTRUMENT_MAP.get(bass.instrument, 33)
        self._midi.addProgramChange(t, channel, 0, program_num)
        self._track_index += 1

        if not bass.rhythm:
            return

        step_duration = 0.5
        for step_idx, step in enumerate(bass.rhythm):
            if step == 'X':
                beat_time = step_idx * step_duration
                pitch = 45  # Default A2
                
                if bass.follow_chord:
                    chord_name = self._get_active_chord(beat_time, chord_timeline)
                    if chord_name:
                        pitch = get_chord_root_midi(chord_name, octave=2)
                
                self._midi.addNote(
                    track=t,
                    channel=channel,
                    pitch=pitch,
                    time=beat_time,
                    duration=step_duration,
                    volume=int(80 * bass.effects.volume),
                )
                self._max_beat = max(self._max_beat, beat_time + step_duration)

    def _get_active_chord(self, beat: float, timeline: list) -> str | None:
        """Find the chord name active at the given beat."""
        for start, end, name in timeline:
            if start <= beat < end:
                return name
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate(program: ProgramNode, output_path: str = "output/track.mid") -> tuple[str, float, list[CompilerMessage]]:
    """Generate a MIDI file from the program AST.

    Args:
        program: Root ProgramNode.
        output_path: Where to write the .mid file.

    Returns:
        Tuple of (output_path_str, duration_s, list[CompilerMessage]).
    """
    gen = MIDIGenerator()
    path, duration = gen.generate(program, output_path)
    return path, duration, gen.get_messages()