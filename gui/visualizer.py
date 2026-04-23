"""
gui/visualizer.py
Mouzikti visualizer widget — Piano Roll and Beat Grid tabs.
Draws on a tkinter Canvas using AST data after each compile.
"""

import sys

import customtkinter as ctk
from tkinter import Canvas

from compiler.ast_nodes import ProgramNode, MelodyNode, BatteryNode, NoteNode, AccordNode
from compiler.music_theory import NOTE_MAP, DURATION_MAP, DRUM_MAP


_FONT_MONO_FAMILY = "Menlo" if sys.platform == "darwin" else "Consolas"


_COLORS = {
    "melody":    "#6366f1",    # Indigo
    "bass":      "#f59e0b",    # Amber
    "kick":      "#ef4444",    # Red
    "snare":     "#8b5cf6",    # Violet
    "hihat":     "#10b981",    # Emerald
    "clap":      "#f97316",    # Orange
    "tom":       "#3b82f6",    # Blue
    "crash":     "#ec4899",    # Pink
    "grid_line": "#334155",    # Slate 700
    "bg":        "#0f172a",    # Deep Slate
    "label":     "#94a3b8",    # Slate 400
    "cell_off":  "#1e293b",    # Slate 800
}


class Visualizer(ctk.CTkFrame):
    """Tabbed visualizer: Piano Roll | Beat Grid."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, corner_radius=8, **kwargs)
        self._active_tab = "piano"
        self._ast: ProgramNode | None = None
        self._playhead_progress: float = 0.0
        self._beat_repeats: int = 1
        # Tab-specific playhead coordinates: { tab_key: (x_start, x_end, h) }
        self._tab_playhead_coords: dict[str, tuple[float, float, int]] = {
            "piano": (0, 0, 0),
            "beat": (0, 0, 0),
            "wave": (0, 0, 0)
        }
        self._build()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Tab bar
        tab_bar = ctk.CTkFrame(self, height=32, corner_radius=0,
                               fg_color=("gray85", "gray20"))
        tab_bar.grid(row=0, column=0, sticky="ew")

        self._tab_btns: dict[str, ctk.CTkButton] = {}
        for key, label in [
            ("piano", "Piano Roll"),
            ("beat", "Beat Grid"),
            ("wave", "Waveform"),
        ]:
            btn = ctk.CTkButton(
                tab_bar,
                text=label,
                width=100, height=26,
                font=ctk.CTkFont(size=11),
                fg_color="transparent",
                hover_color=("gray75", "gray30"),
                command=lambda k=key: self._switch_tab(k),
            )
            btn.pack(side="left", padx=4, pady=3)
            self._tab_btns[key] = btn

        # Canvas
        self._canvas = Canvas(
            self,
            bg=_COLORS["bg"],
            highlightthickness=0,
            bd=0,
        )
        self._canvas.grid(row=1, column=0, sticky="nsew")
        self._canvas.bind("<Configure>", lambda _e: self._redraw())

        self._switch_tab("piano")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_from_ast(self, ast: ProgramNode) -> None:
        """Redraw the visualizer from a freshly compiled AST."""
        self._ast = ast
        self._redraw()

    def clear(self) -> None:
        self._ast = None
        self._canvas.delete("all")

    def set_playhead(self, progress: float) -> None:
        """Set playhead progress ratio (0..1) and redraw only the playhead."""
        self._playhead_progress = max(0.0, min(progress, 1.0))
        coords = self._tab_playhead_coords.get(self._active_tab, (0, 0, 0))
        self._draw_playhead(*coords)

    # ------------------------------------------------------------------
    # Tab switching
    # ------------------------------------------------------------------

    def _switch_tab(self, key: str) -> None:
        self._active_tab = key
        for k, btn in self._tab_btns.items():
            btn.configure(
                fg_color="#6366f1" if k == key else "transparent",
                text_color="white" if k == key else ("gray40", "gray60"),
            )
        self._redraw()

    # ------------------------------------------------------------------
    # Redraw dispatcher
    # ------------------------------------------------------------------

    def _redraw(self) -> None:
        self._canvas.delete("all")
        if self._ast is None:
            self._draw_empty()
            return
        if self._active_tab == "piano":
            self._draw_piano_roll()
        elif self._active_tab == "beat":
            self._draw_beat_grid()
        else:
            self._draw_waveform()

    def _draw_empty(self) -> None:
        w = self._canvas.winfo_width()
        h = self._canvas.winfo_height()
        if w < 2 or h < 2:
            return
        self._canvas.create_text(
            w // 2, h // 2,
            text="Compile a track \n to see the visualizer",
            fill=_COLORS["label"],
            font=(_FONT_MONO_FAMILY, 12),
        )

    # ------------------------------------------------------------------
    # Piano Roll
    # ------------------------------------------------------------------

    def _draw_piano_roll(self) -> None:
        w = self._canvas.winfo_width()
        h = self._canvas.winfo_height()
        if w < 2 or h < 2:
            return

        # Collect all note events from AST
        events: list[tuple[int, float, float, str]] = []  # (midi, start, dur, color)
        if not self._ast or not self._ast.tracks:
            return

        track = self._ast.tracks[0]
        beat_cursor: float = 0.0

        for layer in track.layers:
            if isinstance(layer, MelodyNode):
                color = _COLORS["melody"]
                beat_cursor = 0.0
                for measure in layer.measures:
                    span = max(measure.end - measure.start + 1, 1)
                    for _ in range(span):
                        for stmt in measure.statements:
                            if isinstance(stmt, NoteNode):
                                midi = NOTE_MAP.get(stmt.pitch, 60)
                                dur  = DURATION_MAP.get(stmt.duration, 1.0)
                                events.append((midi, beat_cursor, dur, color))
                                beat_cursor += dur
                            elif isinstance(stmt, AccordNode):
                                dur = DURATION_MAP.get(stmt.duration, 2.0)
                                beat_cursor += dur

        if not events:
            self._draw_empty()
            return

        # Calculate ranges
        min_midi = min(e[0] for e in events) - 2
        max_midi = max(e[0] for e in events) + 2
        max_beat = max(e[1] + e[2] for e in events)
        pitch_range = max(max_midi - min_midi, 8)

        label_w = 36
        row_h   = max(8, (h - 20) // pitch_range)
        x_scale = (w - label_w - 8) / max(max_beat, 1)

        # Grid lines
        for i in range(pitch_range + 1):
            y = 10 + i * row_h
            midi = max_midi - i
            self._canvas.create_line(label_w, y, w, y, fill=_COLORS["grid_line"])
            # Label every C (Do)
            if midi % 12 == 0:
                self._canvas.create_text(
                    label_w - 4, y + row_h // 2,
                    text=f"Do{midi//12 - 1}",
                    fill=_COLORS["label"],
                    font=(_FONT_MONO_FAMILY, 8),
                    anchor="e",
                )

        # Beat bar lines
        for beat in range(int(max_beat) + 1):
            x = label_w + beat * x_scale
            self._canvas.create_line(x, 0, x, h, fill=_COLORS["grid_line"], dash=(2, 4))

        # Notes
        for midi, start, dur, color in events:
            row  = max_midi - midi
            x1   = label_w + start * x_scale
            x2   = label_w + (start + dur) * x_scale - 2
            y1   = 10 + row * row_h + 1
            y2   = 10 + (row + 1) * row_h - 1
            self._canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")

        # Playhead
        self._tab_playhead_coords["piano"] = (label_w, label_w + max_beat * x_scale, h)
        self._draw_playhead(*self._tab_playhead_coords["piano"])

    # ------------------------------------------------------------------
    # Beat Grid
    # ------------------------------------------------------------------

    def _draw_beat_grid(self) -> None:
        w = self._canvas.winfo_width()
        h = self._canvas.winfo_height()
        if w < 2 or h < 2:
            return

        if not self._ast or not self._ast.tracks:
            self._draw_empty()
            return

        track = self._ast.tracks[0]
        battery: BatteryNode | None = None
        for layer in track.layers:
            if isinstance(layer, BatteryNode):
                battery = layer
                break

        if battery is None or not battery.patterns:
            self._draw_empty()
            return

        label_w  = 50
        patterns  = battery.patterns
        num_rows  = len(patterns)
        num_steps = max(len(p.steps) for p in patterns)
        self._beat_repeats = max(battery.repeat, 1)
        row_h     = min(32, (h - 20) // max(num_rows, 1))
        cell_w    = (w - label_w - 12) / num_steps

        for row_idx, pattern in enumerate(patterns):
            y_top    = 10 + row_idx * (row_h + 4)
            color_on = _COLORS.get(pattern.voice, "#7C70D8")

            # Voice label
            self._canvas.create_text(
                label_w - 6, y_top + row_h // 2,
                text=pattern.voice,
                fill=_COLORS["label"],
                font=(_FONT_MONO_FAMILY, 9),
                anchor="e",
            )

            # Cells
            for step_idx, step in enumerate(pattern.steps):
                x1 = label_w + step_idx * cell_w + 1
                x2 = label_w + (step_idx + 1) * cell_w - 1
                fill = color_on if step == 'X' else _COLORS["cell_off"]
                self._canvas.create_rectangle(
                    x1, y_top, x2, y_top + row_h,
                    fill=fill,
                    outline=_COLORS["grid_line"],
                )

            # Bar separators (every 4 steps)
            for step_idx in range(0, num_steps + 1, 4):
                x = label_w + step_idx * cell_w
                self._canvas.create_line(x, y_top, x, y_top + row_h,
                                         fill="#3a3a5e", width=1)
        
        # Playhead
        self._tab_playhead_coords["beat"] = (label_w, label_w + num_steps * cell_w, h)
        self._draw_playhead(*self._tab_playhead_coords["beat"])

    # ------------------------------------------------------------------
    # Waveform (synthetic envelope preview)
    # ------------------------------------------------------------------

    def _draw_waveform(self) -> None:
        w = self._canvas.winfo_width()
        h = self._canvas.winfo_height()
        if w < 2 or h < 2:
            return

        if not self._ast or not self._ast.tracks:
            self._draw_empty()
            return

        track = self._ast.tracks[0]
        bins = max(w // 6, 40)
        energy = [0.0] * bins
        events: list[tuple[float, float, float]] = []

        max_beat = 0.0
        for layer in track.layers:
            if isinstance(layer, MelodyNode):
                beat_cursor = 0.0
                for measure in layer.measures:
                    span = max(measure.end - measure.start + 1, 1)
                    for _ in range(span):
                        for stmt in measure.statements:
                            if isinstance(stmt, NoteNode):
                                dur = DURATION_MAP.get(stmt.duration, 1.0)
                                events.append((beat_cursor, dur, 1.0))
                                beat_cursor += dur
                            elif isinstance(stmt, AccordNode):
                                dur = DURATION_MAP.get(stmt.duration, 2.0)
                                events.append((beat_cursor, dur, 1.3))
                                beat_cursor += dur
                max_beat = max(max_beat, beat_cursor)
            elif isinstance(layer, BatteryNode):
                if not layer.patterns:
                    continue
                steps = len(layer.patterns[0].steps)
                step_duration = 0.5
                battery_total = steps * step_duration * max(layer.repeat, 1)
                max_beat = max(max_beat, battery_total)
                for rep in range(max(layer.repeat, 1)):
                    rep_offset = rep * steps * step_duration
                    for pattern in layer.patterns:
                        gain = 0.6 if pattern.voice == "hihat" else 1.0
                        for step_idx, step in enumerate(pattern.steps):
                            if step == "X":
                                start = rep_offset + (step_idx * step_duration)
                                events.append((start, step_duration, gain))

        if max_beat <= 0:
            self._draw_empty()
            return

        for start, duration, gain in events:
            self._accumulate_energy(energy, start, duration, max_beat, bins, gain)

        max_energy = max(energy) or 1.0
        mid_y = h // 2

        self._canvas.create_line(0, mid_y, w, mid_y, fill=_COLORS["grid_line"])
        prev_x = 0
        prev_y = mid_y
        for i, e in enumerate(energy):
            x = int(i * (w - 1) / max(bins - 1, 1))
            amp = (e / max_energy) * (h * 0.38)
            y = int(mid_y - amp)
            self._canvas.create_line(prev_x, prev_y, x, y, fill=_COLORS["melody"], width=2)
            self._canvas.create_line(prev_x, mid_y + (mid_y - prev_y), x, mid_y + (mid_y - y), fill=_COLORS["melody"], width=2)
            prev_x, prev_y = x, y

        self._canvas.create_text(
            8,
            12,
            text="Waveform preview (envelope from note density)",
            fill=_COLORS["label"],
            font=(_FONT_MONO_FAMILY, 9),
            anchor="w",
        )

        self._tab_playhead_coords["wave"] = (0, w - 1, h)
        self._draw_playhead(*self._tab_playhead_coords["wave"])

    def _accumulate_energy(
        self,
        energy: list[float],
        start: float,
        duration: float,
        total_beats: float,
        bins: int,
        gain: float = 1.0,
    ) -> None:
        """Accumulate a simple energy envelope for waveform preview."""
        span = max(total_beats, 1.0)
        start_bin = int((start / span) * (bins - 1))
        end_bin = int(((start + duration) / span) * (bins - 1))
        for i in range(max(start_bin, 0), min(end_bin + 1, bins)):
            energy[i] += gain

    def _draw_playhead(self, x_start: float, x_end: float, h: int) -> None:
        """Draw a vertical playback cursor line based on current progress."""
        self._canvas.delete("playhead")
        if x_end <= x_start:
            return

        progress = self._playhead_progress
        if self._active_tab == "beat" and self._beat_repeats > 1:
            progress = (progress * self._beat_repeats) % 1.0
            if self._playhead_progress >= 1.0:
                progress = 1.0

        x = x_start + (x_end - x_start) * progress
        # Subtle glow effect
        self._canvas.create_line(x-1, 0, x-1, h, fill="#f59e0b", width=1, stipple="gray50", tags="playhead")
        self._canvas.create_line(x, 0, x, h, fill="#fcd34d", width=2, tags="playhead")
        self._canvas.create_line(x+1, 0, x+1, h, fill="#f59e0b", width=1, stipple="gray50", tags="playhead")