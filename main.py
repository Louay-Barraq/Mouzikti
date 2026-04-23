"""
main.py
Mouzikti entry point.

Usage:
  python main.py                    → launch the GUI
  python main.py test <file.mzt>    → run compiler pipeline in terminal
  python main.py test               → run all examples
"""

import sys
import os


def run_pipeline(source_path: str) -> bool:
    """Run the full compiler pipeline on a .mzt file and print results.

    Returns True if compilation succeeded with no errors.
    """
    from compiler.lexer    import tokenize
    from compiler.parser   import parse
    from compiler.semantic import analyze
    from compiler.codegen  import generate
    from compiler.ast_nodes import pretty_print

    print(f"\n{'='*60}")
    print(f"  Compiling: {source_path}")
    print(f"{'='*60}")

    with open(source_path, "r", encoding="utf-8") as f:
        source = f.read()

    # ── Stage 1: Lexer ───────────────────────────────────────────────
    tokens = tokenize(source)
    print(f"\n[LEXER]  ✓ {len(tokens)} tokens parsed")

    # ── Stage 2: Parser ──────────────────────────────────────────────
    ast, parse_messages = parse(source)
    for msg in parse_messages:
        print(f"[PARSER] {msg}")

    if ast is None or any(msg.level == "error" for msg in parse_messages):
        print("[PARSER] ✗ Parsing failed — cannot continue")
        return False

    print(f"[PARSER] ✓ AST built successfully")
    print()
    pretty_print(ast)

    # ── Stage 3: Semantic ────────────────────────────────────────────
    print()
    sem_messages = analyze(ast)
    has_errors = False
    for msg in sem_messages:
        prefix = "[SEMANTIC]"
        print(f"{prefix} {msg}")
        if msg.level == "error":
            has_errors = True

    if has_errors:
        print("\n[CODEGEN] ✗ Skipping MIDI generation due to semantic errors")
        return False

    # ── Stage 4: Codegen ─────────────────────────────────────────────
    stem = os.path.splitext(os.path.basename(source_path))[0]
    output_path = os.path.join("output", f"{stem}.mid")
    path, duration_s, codegen_messages = generate(ast, output_path)
    for msg in codegen_messages:
        print(f"[CODEGEN] {msg}")

    print(f"\n✅ Success — MIDI written to: {path}\n")
    return True


def run_all_examples() -> None:
    """Run the compiler on all example .mzt files."""
    examples = [
        "examples/simple_melody.mzt",
        "examples/trap_beat.mzt",
        "examples/midnight_vibes.mzt",
        "examples/error_test.mzt",
    ]
    results = {}
    for path in examples:
        if os.path.exists(path):
            results[path] = run_pipeline(path)
        else:
            print(f"\n[SKIP] {path} not found")

    print("\n" + "="*60)
    print("  Test Summary")
    print("="*60)
    for path, ok in results.items():
        status = "✓ PASS" if ok else "✗ FAIL (expected for error_test)"
        print(f"  {status}  {path}")


def launch_gui() -> None:
    """Launch the Mouzikti desktop GUI."""
    try:
        from gui.app import MouziktiApp
        app = MouziktiApp()
        app.mainloop()
    except ImportError as e:
        print(f"[ERROR] Could not load GUI: {e}")
        print("Make sure customtkinter is installed: pip install customtkinter")
        sys.exit(1)


if __name__ == "__main__":
    # Ensure the output directory exists
    os.makedirs("output", exist_ok=True)

    if len(sys.argv) >= 2 and sys.argv[1] == "test":
        if len(sys.argv) >= 3:
            run_pipeline(sys.argv[2])
        else:
            run_all_examples()
    else:
        launch_gui()