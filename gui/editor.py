"""
gui/editor.py
Mouzikti code editor widget with syntax highlighting and line numbers.
"""

import re
import sys
import customtkinter as ctk
from tkinter import Text, END, INSERT


# Token colour rules  (pattern, tag_name)
_HIGHLIGHT_RULES: list[tuple[str, str]] = [
    # Comments first
    (r'//[^\n]*',                                                  'comment'),
    # Strings
    (r'"[^"]*"',                                                   'string'),
    # Keywords
    (r'\b(piste|batterie|mélodie|melodie|basse|mesure|note|accord'
     r'|tempo|tonalité|tonalite|durée|duree|instrument|effets'
     r'|répéter|repeter|si|sinon|suivre|racine|rythme'
     r'|volume|reverb|swing|echo|oui|non)\b',                      'keyword'),
    # Duration literals
    (r'\b(ronde|blanche|noire|croche|double_croche)\b',            'duration'),
    # Note names  La3  Do4  Sol#3
    (r'\b(?:Do|Ré|Re|Mi|Fa|Sol|La|Si)[#b]?[0-9]\b',              'note'),
    # Chord names  La_mineur  Do_majeur
    (r'\b(?:Do|Ré|Re|Mi|Fa|Sol|La|Si)[#b]?_(?:majeur|mineur)\b', 'chord'),
    # Numbers (plain)
    (r'\b\d+(?:\.\d+)?\b',                                         'number'),
    # BPM / mesures units
    (r'\b\d+bpm\b|\b\d+_mesures\b',                               'unit'),
    # Beat X
    (r'\bX\b',                                                     'beat_x'),
]

_TAG_STYLES: dict[str, dict] = {
    'keyword':  {'foreground': '#14b8a6'},
    'duration': {'foreground': '#f59e0b'},
    'note':     {'foreground': '#facc15'},
    'chord':    {'foreground': '#22c55e'},
    'string':   {'foreground': '#2dd4bf'},
    'number':   {'foreground': '#60a5fa'},
    'unit':     {'foreground': '#93c5fd'},
    'comment':  {'foreground': '#64748b', 'font': ("Menlo", 12, 'italic')},
    'beat_x':   {'foreground': '#f97316'},
    'error_ln': {'background': '#3B1818'},   # dark red bg for error lines
}

_FONT_MONO_FAMILY = "Menlo" if sys.platform == "darwin" else "Consolas"
_FONT_UI_FAMILY = ".AppleSystemUIFont" if sys.platform == "darwin" else "TkDefaultFont"


class CodeEditor(ctk.CTkFrame):
    """Syntax-highlighted code editor with line numbers."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, corner_radius=8, **kwargs)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._highlight_job = None
        self._build()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self) -> None:
        # Header
        header = ctk.CTkFrame(self, height=28, corner_radius=0,
                              fg_color="#111827")
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        ctk.CTkLabel(
            header, text="Code Editor",
            font=ctk.CTkFont(family=_FONT_UI_FAMILY, size=11, weight="bold"),
            text_color="#e2e8f0",
        ).pack(side="left", padx=10)
        self._filename_label = ctk.CTkLabel(
            header, text="untitled.mzt",
            font=ctk.CTkFont(family=_FONT_UI_FAMILY, size=10),
            text_color="#94a3b8",
        )
        self._filename_label.pack(side="right", padx=10)

        # Line numbers
        self._line_nums = Text(
            self,
            width=4,
            state="disabled",
            bg="#0b1220",
            fg="#475569",
            font=(_FONT_MONO_FAMILY, 12),
            bd=0,
            highlightthickness=0,
            padx=4,
            relief="flat",
            selectbackground="#1a1a2e",
        )
        self._line_nums.grid(row=1, column=0, sticky="nsew")

        # Main editor
        self._text = Text(
            self,
            bg="#0f172a",
            fg="#e2e8f0",
            insertbackground="#14b8a6",
            selectbackground="#0f766e",
            font=(_FONT_MONO_FAMILY, 12),
            bd=0,
            highlightthickness=0,
            padx=8, pady=8,
            tabs="4",
            undo=True,
            wrap="none",
            relief="flat",
        )
        self._text.grid(row=1, column=1, sticky="nsew")

        # Scrollbar
        sb = ctk.CTkScrollbar(self, command=self._on_scroll)
        sb.grid(row=1, column=2, sticky="ns")
        self._text.configure(yscrollcommand=sb.set)

        # Configure highlight tags
        for tag, style in _TAG_STYLES.items():
            self._text.tag_configure(tag, **style)

        # Bindings
        self._text.bind("<KeyRelease>", self._schedule_highlight)
        self._text.bind("<MouseWheel>", lambda _e: self._sync_line_nums())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_content(self) -> str:
        """Return the current editor text."""
        return self._text.get("1.0", END)

    def set_content(self, text: str) -> None:
        """Replace editor content."""
        self._text.delete("1.0", END)
        self._text.insert("1.0", text)
        self._apply_highlighting()
        self._sync_line_nums()

    def highlight_error_line(self, line_num: int) -> None:
        """Add a red background to the given line number."""
        start = f"{line_num}.0"
        end   = f"{line_num}.end"
        self._text.tag_add("error_ln", start, end)

    def clear_error_highlights(self) -> None:
        """Remove all error line highlights."""
        self._text.tag_remove("error_ln", "1.0", END)

    def set_filename(self, name: str) -> None:
        self._filename_label.configure(text=name)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_scroll(self, *args) -> None:
        self._text.yview(*args)
        self._sync_line_nums()

    def _schedule_highlight(self, _event=None) -> None:
        """Debounce highlighting to avoid re-running on every keystroke."""
        if self._highlight_job:
            self.after_cancel(self._highlight_job)
        self._highlight_job = self.after(300, self._apply_highlighting)
        self._sync_line_nums()

    def _apply_highlighting(self) -> None:
        """Re-run all syntax highlighting rules on the full text."""
        content = self._text.get("1.0", END)
        # Remove all existing highlights
        for tag in _TAG_STYLES:
            if tag != 'error_ln':
                self._text.tag_remove(tag, "1.0", END)

        for pattern, tag in _HIGHLIGHT_RULES:
            for match in re.finditer(pattern, content, re.MULTILINE):
                start_idx = f"1.0 + {match.start()} chars"
                end_idx   = f"1.0 + {match.end()} chars"
                self._text.tag_add(tag, start_idx, end_idx)

    def _sync_line_nums(self) -> None:
        """Redraw the line number gutter to match current content."""
        content = self._text.get("1.0", END)
        num_lines = content.count('\n') + 1

        self._line_nums.configure(state="normal")
        self._line_nums.delete("1.0", END)
        self._line_nums.insert("1.0", "\n".join(str(i) for i in range(1, num_lines + 1)))
        self._line_nums.configure(state="disabled")

        # Sync scroll position
        top_frac = self._text.yview()[0]
        self._line_nums.yview_moveto(top_frac)