"""
gui/app.py
Mouzikti main application window.
Orchestrates the full compiler pipeline and wires all widgets together.
"""


import importlib
import os
import re
import shutil
import subprocess
import sys
import threading

import customtkinter as ctk
from tkinter import filedialog, messagebox

from compiler.lexer    import tokenize
from compiler.parser   import parse
from compiler.semantic import analyze
from compiler.codegen  import generate
from compiler.ast_nodes import (
    BatteryNode,
    BassNode,
    CompilerMessage,
    MelodyNode,
    NoteNode,
    AccordNode,
    RepeatNode,
)
from compiler.music_theory import CHORD_NOTES, DURATION_MAP

from gui.toolbar    import Toolbar
from gui.editor     import CodeEditor
from gui.player     import AudioPlayer
from gui.visualizer import Visualizer
from gui.console    import Console

# ---------------------------------------------------------------------------
# App appearance
# ---------------------------------------------------------------------------

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

_FONT_MONO = ("Menlo", 13) if sys.platform == "darwin" else ("Consolas", 13)
_FONT_UI_FAMILY = ".AppleSystemUIFont" if sys.platform == "darwin" else "TkDefaultFont"
_FONT_MONO_FAMILY = "Menlo" if sys.platform == "darwin" else "Consolas"

_THEME = {
    "bg": "#0f172a",        # Deep Slate
    "panel": "#1e293b",     # Slate 800
    "panel_alt": "#334155", # Slate 700
    "text": "#f8fafc",      # Slate 50
    "muted": "#94a3b8",     # Slate 400
    "accent": "#0f766e",    # Teal 700
    "accent_hover": "#115e59", # Teal 800
    "secondary": "#14b8a6", # Teal 500
}


class MouziktiApp(ctk.CTk):
    """Main Mouzikti application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Mouzikti — Music Compiler")
        self.geometry("1200x720")
        self.minsize(1000, 640)
        self.configure(fg_color=_THEME["bg"])

        self._current_file: str | None = None  # type: ignore
        self._last_midi_path: str | None = None # type: ignore
        self._last_ast = None

        self._build_layout()
        self._bind_shortcuts()
        self._load_default_content()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Toolbar (row 0)
        self.toolbar = Toolbar(
            self,
            on_run=self.run_compiler,
            on_save=self.save_file,
            on_open=self.open_file,
            on_export_midi=self.export_midi,
            on_export_wav=self.export_wav,
            on_export_sheet=self.export_sheet,
        )
        self.toolbar.grid(row=0, column=0, sticky="ew")

        # Main area (row 1)
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=52)
        main_frame.grid_columnconfigure(1, weight=48)

        # Left — editor
        self.editor = CodeEditor(main_frame)
        self.editor.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)

        # Right — player + visualizer
        right_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        right_frame.grid_rowconfigure(1, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        self.player = AudioPlayer(
            right_frame,
            on_progress=self._on_player_progress,
        )
        self.player.grid(row=0, column=0, sticky="ew")

        self.visualizer = Visualizer(right_frame)
        self.visualizer.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        # Bottom — console + status bar
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 4))
        bottom_frame.grid_columnconfigure(0, weight=1)

        self.console = Console(bottom_frame, height=120)
        self.console.grid(row=0, column=0, sticky="ew")

        self._status_var = ctk.StringVar(value="Ready")
        status_bar = ctk.CTkLabel(
            bottom_frame,
            textvariable=self._status_var,
            font=ctk.CTkFont(family=_FONT_MONO_FAMILY, size=11),
            anchor="w",
            text_color=_THEME["muted"],
        )
        status_bar.grid(row=1, column=0, sticky="ew", pady=(2, 0))

    def _bind_shortcuts(self) -> None:
        self.bind("<Control-Return>", lambda _e: self.run_compiler())
        self.bind("<Command-Return>", lambda _e: self.run_compiler())
        self.bind("<space>", lambda e: self.player.play_pause())
        self.bind("<Control-o>",      lambda _e: self.open_file())

    def _load_default_content(self) -> None:
        default = (
            '// Mouzikti — John Lennon: Imagine (Extract)\n'
            '// Press Ctrl+Enter to hear the premium audio engine.\n\n'
            'piste "Imagine" {\n'
            '  tempo: 75bpm\n'
            '  tonalité: "Do majeur"\n'
            '  durée: 8_mesures\n\n'
            '  batterie {\n'
            '    mesure {\n'
            '      kick  : [X . . . . . . . X . . . . . . .]\n'
            '      snare : [. . . . X . . . . . . . X . . .]\n'
            '      hihat : [X . X . X . X . X . X . X . X .]\n'
            '    }\n'
            '    répéter 8\n'
            '  }\n\n'
            '  mélodie instrument: piano {\n'
            '    mesure 1..2 { accord(Do_majeur, blanche) accord(Fa_majeur, blanche) }\n'
            '    mesure 3..4 { accord(Do_majeur, blanche) accord(Fa_majeur, blanche) }\n'
            '    mesure 5..6 { accord(Do_majeur, blanche) accord(Fa_majeur, blanche) }\n'
            '    mesure 7..8 { accord(Do_majeur, blanche) accord(Fa_majeur, blanche) }\n'
            '  }\n'
            '}\n'
        )
        self.editor.set_content(default)

    # ------------------------------------------------------------------
    # Compiler pipeline
    # ------------------------------------------------------------------

    def run_compiler(self) -> None:
        """Orchestrate the full compilation pipeline."""
        source = self.editor.get_content()
        self.console.clear()
        self.editor.clear_error_highlights()
        self._set_status("Compiling…")

        # Run in a background thread to keep GUI responsive
        threading.Thread(target=self._compile_thread, args=(source,), daemon=True).start()

    def _compile_thread(self, source: str) -> None:
        """Background compilation — posts results back to main thread."""
        try:
            # Stage 1: Lex
            tokens = tokenize(source)
            self._post(self.console.log_ok, f"Lexer: {len(tokens)} tokens parsed")

            # Stage 2: Parse
            ast, parse_msgs = parse(source)
            for msg in parse_msgs:
                self._post_message(msg)

            if ast is None or any(m.level == "error" for m in parse_msgs):
                self._post(self._set_status, "✗ Parse failed")
                return

            self._post(self.console.log_ok, "Parser: AST built successfully")
            self._last_ast = ast

            # Stage 3: Semantic
            sem_msgs = analyze(ast)
            for msg in sem_msgs:
                self._post_message(msg)

            error_lines = [m.line for m in sem_msgs if m.level == "error" and m.line > 0]
            for ln in error_lines:
                self._post(self.editor.highlight_error_line, ln)

            if any(m.level == "error" for m in sem_msgs):
                self._post(self._set_status, "✗ Semantic errors — MIDI not generated")
                return

            # Stage 4: Codegen
            output_path = os.path.join("outputs", "midi", "track.mid")
            midi_path, duration_s, codegen_msgs = generate(ast, output_path)
            for msg in codegen_msgs:
                self._post_message(msg)

            self._last_midi_path = midi_path

            # Update UI
            track = ast.tracks[0] if ast.tracks else None
            instruments = self._collect_instruments(ast)

            self._post(self.player.load, midi_path, duration_s)
            if track:
                self._post(self.player.update_track_info, track.name, instruments, track.tempo, track.key)
            self._post(self.visualizer.update_from_ast, ast)
            self._post(self.toolbar.update_badges, ast)
            self._post(self._set_status,
                       f"✓ Compiled — {midi_path}")

        except Exception as exc:
            self._post(self.console.log_error, f"Unexpected error: {exc}")
            self._post(self._set_status, "✗ Compilation failed")

    def _post(self, fn, *args, **kwargs) -> None:
        """Schedule a GUI update on the main thread."""
        self.after(0, lambda: fn(*args, **kwargs))

    def _post_message(self, msg: CompilerMessage) -> None:
        if msg.level == "error":
            self._post(self.console.log_error, msg.message, msg.line, msg.suggestion)
        elif msg.level == "warning":
            self._post(self.console.log_warning, msg.message, msg.line)
        elif msg.level == "ok":
            self._post(self.console.log_ok, msg.message)
        else:
            self._post(self.console.log_info, msg.message)

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def save_file(self) -> None:
        path = self._current_file or filedialog.asksaveasfilename(
            defaultextension=".mzt",
            filetypes=[("Mouzikti files", "*.mzt"), ("All files", "*.*")],
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.editor.get_content())
        self._current_file = path
        self._set_status(f"Saved → {path}")

    def open_file(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("Mouzikti files", "*.mzt"), ("All files", "*.*")]
        )
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        self.editor.set_content(content)
        self._current_file = path
        self._set_status(f"Opened → {path}")

    def export_midi(self) -> None:
        if not self._last_midi_path:
            messagebox.showinfo("Export MIDI", "Compile your track first (Ctrl+Enter)")
            return
        dest = filedialog.asksaveasfilename(
            defaultextension=".mid",
            filetypes=[("MIDI files", "*.mid"), ("All files", "*.*")],
            initialfile="mouzikti_track.mid",
        )
        if not dest:
            return
        import shutil
        shutil.copy2(self._last_midi_path, dest)
        self._set_status(f"MIDI exported → {dest}")

    def export_wav(self) -> None:
        """Export WAV from the last generated MIDI using FluidSynth backends."""
        if not self._last_midi_path:
            messagebox.showinfo("Export WAV", "Compile your track first (Ctrl+Enter)")
            return

        dest = filedialog.asksaveasfilename(
            defaultextension=".wav",
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")],
            initialdir=os.path.join(os.getcwd(), "outputs", "wav"),
            initialfile="mouzikti_track.wav",
        )
        if not dest:
            return

        binary = self._find_fluidsynth_binary()
        soundfont = self._find_soundfont()

        if not binary:
            messagebox.showerror(
                "Export WAV",
                "FluidSynth binary not found in PATH.\n"
                "Install with: brew install fluid-synth",
            )
            return

        if not soundfont:
            messagebox.showerror(
                "Export WAV",
                "SoundFont (.sf2) not found.\n"
                "Set FLUIDSYNTH_SOUNDFONT or place default.sf2 in the project root.",
            )
            return

        cmd = [
            binary,
            "-ni",
            soundfont,
            self._last_midi_path,
            "-F",
            dest,
            "-r",
            "44100",
        ]

        self._set_status("Exporting WAV…")
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if proc.returncode == 0:
                self._set_status(f"WAV exported → {dest}")
                return

            details = proc.stderr.strip() or proc.stdout.strip() or "Unknown FluidSynth error"
            self.console.log_error(f"WAV export failed: {details}")
            messagebox.showerror("Export WAV", f"FluidSynth failed:\n\n{details}")
        except Exception as exc:
            self.console.log_error(f"WAV export failed: {exc}")
            messagebox.showerror("Export WAV", f"An error occurred:\n\n{exc}")

    def export_sheet(self) -> None:
        """Export a basic MusicXML note sheet from the first melody layer."""
        if not self._last_ast:
            messagebox.showinfo("Export Sheet", "Compile your track first (Ctrl+Enter)")
            return

        dest = filedialog.asksaveasfilename(
            defaultextension=".musicxml",
            filetypes=[("MusicXML files", "*.musicxml"), ("All files", "*.*")],
            initialfile="mouzikti_sheet.musicxml",
        )
        if not dest:
            return

        try:
            xml = self._ast_to_musicxml(self._last_ast)
            with open(dest, "w", encoding="utf-8") as f:
                f.write(xml)
            self._set_status(f"Sheet exported → {dest}")
        except Exception as exc:
            messagebox.showerror("Export Sheet", f"Sheet export failed: {exc}")

    def _find_fluidsynth_binary(self) -> str | None:
        """Find fluidsynth binary from env, PATH, or common macOS install paths."""
        candidates = [
            os.environ.get("FLUIDSYNTH_PATH", ""),
            shutil.which("fluidsynth") or "",
            "/opt/homebrew/bin/fluidsynth",
            "/usr/local/bin/fluidsynth",
            "/usr/bin/fluidsynth",
        ]
        for path in candidates:
            if path and os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        return None

    def _find_soundfont(self) -> str | None:
        """Find a usable .sf2 soundfont path."""
        # Check current directory for default.sf2 first (priority)
        local_default = os.path.join(os.getcwd(), "default.sf2")
        if os.path.isfile(local_default):
            return local_default

        candidates = [
            os.environ.get("FLUIDSYNTH_SOUNDFONT", ""),
            "soundfont.sf2",
            os.path.expanduser("~/.fluidsynth/default_sound_font.sf2"),
            "/opt/homebrew/share/soundfonts/FluidR3_GM.sf2",
            "/Library/Audio/Sounds/Banks/FluidR3_GM.sf2",
            "/Library/Audio/Sounds/Banks/gs_instruments.sf2",
            "/usr/local/share/soundfonts/FluidR3_GM.sf2",
            "/System/Library/Sounds/FluidR3_GM.sf2",
        ]
        for path in candidates:
            if path and os.path.isfile(path):
                return path
        return None

    def _on_player_progress(self, progress: float) -> None:
        """Update visualizer playhead from player progress."""
        self.visualizer.set_playhead(progress)

    def _estimate_track_duration_s(self, ast) -> float:
        if not ast or not ast.tracks:
            return 0.0

        track = ast.tracks[0]
        tempo = max(track.tempo, 20)
        battery_beats = 0.0
        melody_beats = 0.0
        bass_beats = 0.0

        for layer in track.layers:
            if isinstance(layer, BatteryNode):
                if layer.patterns:
                    steps = len(layer.patterns[0].steps)
                    battery_beats = steps * 0.5 * max(layer.repeat, 1)
            elif isinstance(layer, MelodyNode):
                melody_beats = self._melody_beats(layer)
            elif isinstance(layer, BassNode):
                if layer.rhythm:
                    bass_beats = len(layer.rhythm) * 0.5

        total_beats = max(battery_beats, melody_beats, bass_beats, 0.0)
        return (total_beats * 60.0) / tempo if total_beats else 0.0

    def _melody_beats(self, melody: MelodyNode) -> float:
        beats = 0.0
        for measure in melody.measures:
            span = max(measure.end - measure.start + 1, 1)
            beats_per_measure = 0.0
            for stmt in measure.statements:
                if isinstance(stmt, NoteNode):
                    beats_per_measure += DURATION_MAP.get(stmt.duration, 1.0)
                elif isinstance(stmt, AccordNode):
                    beats_per_measure += DURATION_MAP.get(stmt.duration, 2.0)
                elif isinstance(stmt, RepeatNode):
                    beats_per_measure += self._repeat_beats(stmt)
            beats += beats_per_measure * span
        return beats

    def _repeat_beats(self, repeat: RepeatNode) -> float:
        body_beats = 0.0
        for stmt in repeat.body:
            if isinstance(stmt, NoteNode):
                body_beats += DURATION_MAP.get(stmt.duration, 1.0)
            elif isinstance(stmt, AccordNode):
                body_beats += DURATION_MAP.get(stmt.duration, 2.0)
        return body_beats * max(repeat.count, 0)

    def _collect_instruments(self, ast) -> str:
        if not ast or not ast.tracks:
            return "—"
        track = ast.tracks[0]
        instruments: list[str] = []
        for layer in track.layers:
            if isinstance(layer, MelodyNode):
                instruments.append(layer.instrument)
            elif isinstance(layer, BassNode):
                instruments.append(layer.instrument)
            elif isinstance(layer, BatteryNode):
                instruments.append("drums")
        return " · ".join(instruments) if instruments else "—"

    def _ast_to_musicxml(self, ast) -> str:
        """Convert the first melody layer of an AST into a minimal MusicXML score."""
        if not ast.tracks:
            raise ValueError("No track found in AST")

        track = ast.tracks[0]
        melody = None
        for layer in track.layers:
            if hasattr(layer, "measures") and hasattr(layer, "instrument"):
                melody = layer
                break
        if melody is None:
            raise ValueError("No melody layer found")

        duration_divisions = {
            "ronde": 16,
            "blanche": 8,
            "noire": 4,
            "croche": 2,
            "double_croche": 1,
        }
        duration_type = {
            "ronde": "whole",
            "blanche": "half",
            "noire": "quarter",
            "croche": "eighth",
            "double_croche": "16th",
        }

        def note_xml(step: str, octave: int, duration_name: str, alter: int = 0, chord: bool = False) -> str:
            chord_tag = "<chord/>" if chord else ""
            alter_tag = f"<alter>{alter}</alter>" if alter else ""
            return (
                "      <note>\n"
                f"        {chord_tag}\n"
                "        <pitch>\n"
                f"          <step>{step}</step>\n"
                f"          {alter_tag}\n"
                f"          <octave>{octave}</octave>\n"
                "        </pitch>\n"
                f"        <duration>{duration_divisions[duration_name]}</duration>\n"
                f"        <type>{duration_type[duration_name]}</type>\n"
                "      </note>\n"
            )

        def parse_solfege_pitch(token: str) -> tuple[str, int, int]:
            m = re.fullmatch(r"(Do|Ré|Re|Mi|Fa|Sol|La|Si)([#b]?)(\d)", token)
            if not m:
                return "C", 4, 0
            base, accidental, octave_s = m.groups()
            step_map = {
                "Do": "C", "Ré": "D", "Re": "D", "Mi": "E", "Fa": "F",
                "Sol": "G", "La": "A", "Si": "B",
            }
            alter = 1 if accidental == "#" else (-1 if accidental == "b" else 0)
            return step_map.get(base, "C"), int(octave_s), alter

        def base_to_pitch(base: str, octave: int = 4) -> tuple[str, int, int]:
            m = re.fullmatch(r"(Do|Ré|Re|Mi|Fa|Sol|La|Si)([#b]?)", base)
            if not m:
                return "C", octave, 0
            root, accidental = m.groups()
            step_map = {
                "Do": "C", "Ré": "D", "Re": "D", "Mi": "E", "Fa": "F",
                "Sol": "G", "La": "A", "Si": "B",
            }
            alter = 1 if accidental == "#" else (-1 if accidental == "b" else 0)
            return step_map.get(root, "C"), octave, alter

        measure_chunks: list[str] = []
        measure_no = 1
        for m_block in melody.measures:
            span = max(m_block.end - m_block.start + 1, 1)
            for _ in range(span):
                content = []
                if measure_no == 1:
                    content.append(
                        "      <attributes>\n"
                        "        <divisions>4</divisions>\n"
                        "        <key><fifths>0</fifths></key>\n"
                        "        <time><beats>4</beats><beat-type>4</beat-type></time>\n"
                        "        <clef><sign>G</sign><line>2</line></clef>\n"
                        "      </attributes>\n"
                    )

                for stmt in m_block.statements:
                    if hasattr(stmt, "pitch") and hasattr(stmt, "duration"):
                        step, octave, alter = parse_solfege_pitch(stmt.pitch)
                        content.append(note_xml(step, octave, stmt.duration, alter=alter))
                    elif hasattr(stmt, "name") and hasattr(stmt, "duration"):
                        chord_notes = CHORD_NOTES.get(stmt.name, [])
                        for idx, base in enumerate(chord_notes):
                            step, octave, alter = base_to_pitch(base, octave=4)
                            content.append(note_xml(step, octave, stmt.duration, alter=alter, chord=(idx > 0)))

                measure_chunks.append(
                    f"    <measure number=\"{measure_no}\">\n"
                    + "".join(content)
                    + "    </measure>\n"
                )
                measure_no += 1

        title = track.name.replace("&", "and").replace("<", "").replace(">", "")
        return (
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            "<!DOCTYPE score-partwise PUBLIC \"-//Recordare//DTD MusicXML 3.1 Partwise//EN\"\n"
            "  \"http://www.musicxml.org/dtds/partwise.dtd\">\n"
            "<score-partwise version=\"3.1\">\n"
            "  <work><work-title>" + title + "</work-title></work>\n"
            "  <part-list>\n"
            "    <score-part id=\"P1\"><part-name>Melody</part-name></score-part>\n"
            "  </part-list>\n"
            "  <part id=\"P1\">\n"
            + "".join(measure_chunks)
            + "  </part>\n"
            "</score-partwise>\n"
        )

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _set_status(self, text: str) -> None:
        self._status_var.set(f"  {text}")