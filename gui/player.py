"""
gui/player.py
Mouzikti audio player widget.
Handles MIDI playback via pygame.mixer.
"""

from typing import Any, cast
import os
import sys

import customtkinter as ctk

try:
    import pygame as _pygame
    import time
    _pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    pygame: Any | None = _pygame
    _PYGAME_OK = True
except Exception:
    pygame = None
    _PYGAME_OK = False
    import time


_FONT_UI_FAMILY = ".AppleSystemUIFont" if sys.platform == "darwin" else "TkDefaultFont"
_COLORS = {
    "accent": "#0f766e",
    "accent_hover": "#115e59",
    "muted": "#64748b",
    "border": "#334155",
}


class AudioPlayer(ctk.CTkFrame):
    """Audio player widget with transport controls and progress bar."""

    def __init__(self, master, on_progress=None, **kwargs) -> None:
        super().__init__(master, corner_radius=8, **kwargs)
        self._midi_path: str | None = None
        self._playing: bool = False
        self._paused: bool = False
        self._duration_s: float = 0.0
        self._start_time: float = 0.0
        self._elapsed_base: float = 0.0
        self._poll_job = None
        self._on_progress = on_progress

        self._build()

    def _audio_ready(self) -> bool:
        """Return True when pygame audio is available and initialized."""
        return _PYGAME_OK and pygame is not None

    def _music(self) -> Any | None:
        """Return pygame.mixer.music when available, otherwise None."""
        pygame_obj = pygame
        if not _PYGAME_OK or pygame_obj is None:
            return None
        return cast(Any, pygame_obj.mixer.music)

    def _set_transport_state(self, enabled: bool) -> None:
        """Enable/disable transport buttons based on file/audio availability."""
        state = "normal" if enabled else "disabled"
        self._rewind_btn.configure(state=state)
        self._play_btn.configure(state=state)
        self._stop_btn.configure(state=state)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self) -> None:
        pad = {"padx": 12, "pady": 6}

        # Track info row
        info_row = ctk.CTkFrame(self, fg_color="transparent")
        info_row.pack(fill="x", **pad)

        # Centered track name
        self._track_name = ctk.CTkLabel(
            info_row, text="No track compiled yet",
            font=ctk.CTkFont(family=_FONT_UI_FAMILY, size=16, weight="bold"),
            anchor="center",
        )
        self._track_name.pack(fill="x", expand=True, pady=(10, 5))

        # Progress bar
        self._progress = ctk.CTkProgressBar(self, height=6)
        self._progress.pack(fill="x", padx=12, pady=(4, 0))
        self._progress.set(0)

        # Time row
        time_row = ctk.CTkFrame(self, fg_color="transparent")
        time_row.pack(fill="x", padx=12, pady=(2, 4))
        self._elapsed_lbl = ctk.CTkLabel(
            time_row, text="0:00",
            font=ctk.CTkFont(family=_FONT_UI_FAMILY, size=11),
            text_color=_COLORS["muted"],
        )
        self._elapsed_lbl.pack(side="left")
        self._total_lbl = ctk.CTkLabel(
            time_row, text="0:00",
            font=ctk.CTkFont(family=_FONT_UI_FAMILY, size=11),
            text_color=_COLORS["muted"],
        )
        self._total_lbl.pack(side="right")

        # Transport controls
        ctrl_row = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_row.pack(pady=(0, 6))

        def _btn(text, cmd, size=28, main=False):
            return ctk.CTkButton(
                ctrl_row,
                text=text,
                width=size, height=size,
                corner_radius=size // 2,
                font=ctk.CTkFont(family=_FONT_UI_FAMILY, size=14 if main else 12),
                command=cmd,
                fg_color=_COLORS["accent"] if main else "transparent",
                hover_color=_COLORS["accent_hover"] if main else ("gray85", "gray30"),
                border_width=0 if main else 1,
                border_color=_COLORS["border"],
            )

        self._rewind_btn = _btn("⏮", self.rewind)
        self._rewind_btn.pack(side="left", padx=6)
        self._play_btn = _btn("▶", self.play_pause, size=40, main=True)
        self._play_btn.pack(side="left", padx=6)
        self._stop_btn = _btn("⏹", self.stop)
        self._stop_btn.pack(side="left", padx=6)

        self._set_transport_state(False)

        # Volume
        vol_row = ctk.CTkFrame(self, fg_color="transparent")
        vol_row.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkLabel(
            vol_row,
            text="Vol",
            font=ctk.CTkFont(family=_FONT_UI_FAMILY, size=11),
            text_color=_COLORS["muted"],
        ).pack(side="left", padx=(0, 6))
        self._vol_slider = ctk.CTkSlider(vol_row, from_=0, to=1,
                                         number_of_steps=20,
                                         command=self._on_volume)
        self._vol_slider.set(0.8)
        self._vol_slider.pack(side="left", fill="x", expand=True)

        if not _PYGAME_OK:
            ctk.CTkLabel(self, text="⚠ Audio unavailable",
                         font=ctk.CTkFont(size=10),
                         text_color=("#E24B4A", "#E24B4A")).pack()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, midi_path: str, duration_s: float = 0.0) -> None:
        """Load a MIDI file for playback."""
        self.stop()
        self._midi_path = midi_path
        self._duration_s = duration_s
        name = os.path.basename(midi_path).replace(".mid", "")
        self._track_name.configure(text=name)
        self._progress.set(0)
        self._total_lbl.configure(text=self._format_time(duration_s))
        if callable(self._on_progress):
            self._on_progress(0.0)
        self._play_btn.configure(text="▶")
        self._set_transport_state(self._audio_ready())

    def set_duration(self, duration_s: float) -> None:
        """Update displayed total duration without reloading the current track."""
        self._duration_s = max(duration_s, 0.0)
        self._total_lbl.configure(text=self._format_time(self._duration_s))

    def play_pause(self) -> None:
        """Toggle play / pause."""
        music = self._music()
        if music is None or not self._midi_path:
            return
        
        if self._playing:
            music.pause()
            self._playing = False
            self._paused = True
            self._elapsed_base += time.perf_counter() - self._start_time
            self._play_btn.configure(text="▶")
            if self._poll_job:
                self.after_cancel(self._poll_job)
        else:
            if self._paused:
                music.unpause()
            else:
                music.load(self._midi_path)
                music.play()
            
            self._playing = True
            self._paused = False
            self._start_time = time.perf_counter()
            self._play_btn.configure(text="⏸")
            self._start_poll()

    def stop(self) -> None:
        """Stop playback and reset position."""
        music = self._music()
        if music is not None:
            music.stop()
        self._playing = False
        self._paused = False
        self._elapsed_base = 0.0
        self._play_btn.configure(text="▶")
        self._progress.set(0)
        if callable(self._on_progress):
            self._on_progress(0.0)
        self._elapsed_lbl.configure(text="0:00")
        if self._poll_job:
            self.after_cancel(self._poll_job)
            self._poll_job = None

        if not self._midi_path:
            self._set_transport_state(False)

    def rewind(self) -> None:
        """Stop and reload from beginning."""
        self.stop()

    def update_track_info(self, name: str, instruments: str, bpm: int, key: str) -> None:
        """Update track info labels."""
        self._track_name.configure(text=name)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_volume(self, val: float) -> None:
        music = self._music()
        if music is not None:
            music.set_volume(val)

    def _start_poll(self) -> None:
        """Poll playback position every 50ms to update progress bar."""
        self._poll()

    def _poll(self) -> None:
        if not self._playing:
            return
        music = self._music()
        if music is not None and not music.get_busy():
            self.stop()
            return

        # Calculate high-resolution elapsed time
        elapsed = self._elapsed_base + (time.perf_counter() - self._start_time)
        
        if self._duration_s > 0:
            current = min(elapsed / self._duration_s, 1.0)
        else:
            current = 0.0

        self._progress.set(current)
        shown_elapsed = min(elapsed, self._duration_s) if self._duration_s > 0 else elapsed
        self._elapsed_lbl.configure(text=self._format_time(shown_elapsed))
        
        if callable(self._on_progress):
            self._on_progress(current)
            
        self._poll_job = self.after(50, self._poll) # Faster polling for smoothness

    def _format_time(self, seconds: float) -> str:
        """Format seconds into MM:SS."""
        s = int(max(seconds, 0))
        mins = s // 60
        secs = s % 60
        return f"{mins}:{secs:02d}"