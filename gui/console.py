"""
gui/console.py
Mouzikti console widget — displays coloured compiler output.
"""

import customtkinter as ctk
import sys
from tkinter import Text, END, DISABLED, NORMAL


_FONT_MONO_FAMILY = "Menlo" if sys.platform == "darwin" else "Consolas"
_FONT_UI_FAMILY = ".AppleSystemUIFont" if sys.platform == "darwin" else "TkDefaultFont"


class Console(ctk.CTkFrame):
    """Read-only console for compiler messages with colour-coded levels."""

    def __init__(self, master, height: int = 120, **kwargs) -> None:
        super().__init__(master, corner_radius=8, height=height, **kwargs)
        self.pack_propagate(False)
        self._build()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self) -> None:
        # Header
        header = ctk.CTkFrame(self, height=24, corner_radius=0,
                              fg_color="#111827")
        header.pack(fill="x")
        ctk.CTkLabel(
            header, text="Console",
            font=ctk.CTkFont(family=_FONT_UI_FAMILY, size=10, weight="bold"),
            text_color="#e2e8f0",
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            header, text="Clear", width=48, height=18,
            font=ctk.CTkFont(family=_FONT_UI_FAMILY, size=9),
            fg_color="transparent",
            text_color="#cbd5e1",
            hover_color="#1f2937",
            command=self.clear,
        ).pack(side="right", padx=4, pady=2)

        # Text widget
        self._text = Text(
            self,
            state=DISABLED,
            bg="#0b1220",
            fg="#f1f5f9",
            font=(_FONT_MONO_FAMILY, 11),
            bd=0,
            highlightthickness=0,
            padx=12, pady=8,
            wrap="word",
            relief="flat",
            insertbackground="#6366f1",
        )
        self._text.pack(fill="both", expand=True)

        # Tags
        self._text.tag_configure("ok",      foreground="#10b981")
        self._text.tag_configure("warning", foreground="#f59e0b")
        self._text.tag_configure("error",   foreground="#ef4444")
        self._text.tag_configure("info",    foreground="#94a3b8")
        self._text.tag_configure("dim",     foreground="#475569")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Clear all console content."""
        self._write("", clear=True)

    def log_ok(self, message: str) -> None:
        self._write(f"✓ {message}\n", tag="ok")

    def log_warning(self, message: str, line: int = 0) -> None:
        loc = f" (line {line})" if line else ""
        self._write(f"⚠ [WARNING]{loc} — {message}\n", tag="warning")

    def log_error(self, message: str, line: int = 0, suggestion: str = "") -> None:
        loc = f" (line {line})" if line else ""
        text = f"✗ [ERROR]{loc} — {message}\n"
        if suggestion:
            text += f"    → {suggestion}\n"
        self._write(text, tag="error")

    def log_info(self, message: str) -> None:
        self._write(f"→ {message}\n", tag="info")

    def log_compiler_results(self, messages) -> None:
        """Batch log from a list of CompilerMessage objects."""
        for msg in messages:
            if msg.level == "error":
                self.log_error(msg.message, msg.line, msg.suggestion)
            elif msg.level == "warning":
                self.log_warning(msg.message, msg.line)
            elif msg.level == "ok":
                self.log_ok(msg.message)
            else:
                self.log_info(msg.message)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _write(self, text: str, tag: str = "info", clear: bool = False) -> None:
        self._text.configure(state=NORMAL)
        if clear:
            self._text.delete("1.0", END)
        else:
            self._text.insert(END, text, tag)
            self._text.see(END)
        self._text.configure(state=DISABLED)