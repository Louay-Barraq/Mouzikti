"""
gui/toolbar.py
Mouzikti toolbar widget — Run, Export, Save, Open buttons + live badges.
"""

import sys

import customtkinter as ctk
from compiler.ast_nodes import ProgramNode


_FONT_UI_FAMILY = ".AppleSystemUIFont" if sys.platform == "darwin" else "TkDefaultFont"


class Toolbar(ctk.CTkFrame):
    """Top toolbar with action buttons and live track metadata badges."""

    def __init__(
        self,
        master,
        on_run,
        on_save,
        on_open,
        on_export_midi,
        on_export_wav,
        on_export_sheet,
    ) -> None:
        super().__init__(master, height=44, corner_radius=0)
        self.pack_propagate(False)

        self._on_run         = on_run
        self._on_save        = on_save
        self._on_open        = on_open
        self._on_export_midi = on_export_midi
        self._on_export_wav  = on_export_wav
        self._on_export_sheet = on_export_sheet

        self._bpm_var  = ctk.StringVar(value="— BPM")
        self._key_var  = ctk.StringVar(value="— key")
        self._dur_var  = ctk.StringVar(value="— bars")

        self._build()

    def _build(self) -> None:
        self.configure(fg_color="#111827")

        # App title
        ctk.CTkLabel(
            self, text="Mouzikti",
            font=ctk.CTkFont(family=_FONT_UI_FAMILY, size=15, weight="bold"),
            text_color="#e2e8f0",
        ).pack(side="left", padx=(12, 4))

        ctk.CTkLabel(
            self, text="v1.0",
            font=ctk.CTkFont(family=_FONT_UI_FAMILY, size=11),
            text_color="#94a3b8",
        ).pack(side="left", padx=(0, 12))

        _sep(self).pack(side="left", fill="y", pady=8, padx=4)

        # Action buttons
        ctk.CTkButton(
            self, text="▶ Run",
            width=80, height=32,
            corner_radius=8,
            font=ctk.CTkFont(family=_FONT_UI_FAMILY, size=13, weight="bold"),
            fg_color="#0f766e", hover_color="#115e59",
            command=self._on_run,
            text_color="#f8fafc",
        ).pack(side="left", padx=6)

        def _small_btn(text, cmd):
            return ctk.CTkButton(
                self, text=text,
                width=100, height=32,
                corner_radius=8,
                font=ctk.CTkFont(family=_FONT_UI_FAMILY, size=12),
                fg_color="transparent",
                border_width=1,
                border_color="#334155",
                hover_color="#1f2937",
                text_color="#e2e8f0",
                command=cmd
            ).pack(side="left", padx=4)

        _small_btn("Export MIDI", self._on_export_midi)
        _small_btn("Export WAV", self._on_export_wav)
        _small_btn("Export Sheet", self._on_export_sheet)

        _sep(self).pack(side="left", fill="y", pady=8, padx=4)

        ctk.CTkButton(
            self, text="Save",
            width=80, height=32,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            border_color="#334155",
            hover_color="#1f2937",
            text_color="#e2e8f0",
            font=ctk.CTkFont(family=_FONT_UI_FAMILY, size=12),
            command=self._on_save,
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            self, text="Open",
            width=80, height=32,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            border_color="#334155",
            hover_color="#1f2937",
            text_color="#e2e8f0",
            font=ctk.CTkFont(family=_FONT_UI_FAMILY, size=12),
            command=self._on_open,
        ).pack(side="left", padx=4)

        # Badges (right side)
        for var in (self._bpm_var, self._key_var, self._dur_var):
            ctk.CTkLabel(
                self,
                textvariable=var,
                font=ctk.CTkFont(family=_FONT_UI_FAMILY, size=11),
                fg_color="#1f2937",
                text_color="#cbd5e1",
                corner_radius=6,
                padx=8, pady=2,
            ).pack(side="right", padx=4)

        ctk.CTkLabel(self, text="").pack(side="right", padx=4)   # spacer

    def update_badges(self, ast: ProgramNode) -> None:
        """Update BPM / key / duration badges from the compiled AST."""
        if not ast or not ast.tracks:
            return
        track = ast.tracks[0]
        self._bpm_var.set(f"{track.tempo} BPM")
        self._key_var.set(track.key or "—")
        self._dur_var.set(f"{track.duration} bars")


def _sep(master) -> ctk.CTkFrame:
    """Thin vertical separator."""
    return ctk.CTkFrame(master, width=1, fg_color="#334155")