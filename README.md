# Mouzikti

Mouzikti is a music-focused DSL that compiles .mzt source files into MIDI.
It includes a desktop GUI editor/player and a CLI test mode.

## Requirements

- Python 3.10+
- Dependencies from requirements.txt:
	- ply
	- midiutil
	- pygame
	- customtkinter

## Installation

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Running

Launch GUI:

```bash
python main.py
```

Run compiler on one file:

```bash
python main.py test examples/simple_melody.mzt
```

Run all bundled examples:

```bash
python main.py test
```

## Toolbar Actions

- **Run**: Compile and play current editor content.
- **Export MIDI**: Save the generated MIDI file.
- **Export WAV**: Render and save high-fidelity audio using FluidSynth.
- **Export Sheet**: Export the melody layer as a MusicXML sheet.
- **Save/Open**: Standard `.mzt` file operations.
- **Live Badges**: Real-time display of BPM, Key, and Duration from the compiled AST.

## Language Quick Reference

Top-level structure:

```mzt
piste "Track Name" {
	tempo: 120bpm
	tonalité: "La mineur"
	durée: 8_mesures

	batterie {
		mesure {
			kick  : [X . . . X . . . X . . . X . . .]
			snare : [. . . . X . . . . . . . X . . .]
			hihat : [X X X X X X X X X X X X X X X X]
		}
		effets { reverb: 0.2, swing: 0.1 }
		répéter 4
	}

	mélodie instrument: piano {
		mesure 1..4 {
			note(La3, noire)
			accord(La_mineur, blanche)
		}
		effets { volume: 0.8, echo: 0.2 }
	}

	basse instrument: basse_électrique {
		suivre accord_actuel racine: oui
		rythme: [X . X . . X . .]
	}
}
```

## Supported Keywords

- `piste`
- `batterie`
- `mélodie` / `melodie`
- `basse`
- `mesure`
- `note`
- `accord`
- `tempo`
- `tonalité` / `tonalite`
- `durée` / `duree`
- `instrument`
- `effets`
- `répéter` / `repeter`
- `si`
- `sinon`
- `suivre`
- `racine`
- `rythme`
- `volume`
- `reverb`
- `swing`
- `echo`
- `oui`
- `non`

## Supported Durations

- `ronde`, `blanche`, `noire`, `croche`, `double_croche`, `triple_croche`
- Dotted versions: `blanche_pointée`, `noire_pointée`, `croche_pointée`

## Supported Instruments

- piano
- guitare
- basse_électrique / basse_electrique
- violon
- flûte / flute
- orgue
- synthé / synthe

## Supported Drum Voices

- `kick`, `snare`, `hihat`, `clap`, `tom`, `crash`

## Supported Scales & Chords

- **Scales**: Do majeur/mineur, Sol majeur, Ré majeur/mineur, La majeur/mineur, Mi majeur/mineur, Fa majeur, Si majeur, Pentatonique, Blues.
- **Chords**: Do_majeur/mineur, Ré_majeur/mineur, Mi_majeur/mineur, Fa_majeur/mineur, Sol_majeur/mineur, La_majeur/mineur, Si_majeur/mineur.

## GUI & Visualization

Mouzikti features a triple-view visualizer:
- **Piano Roll**: Displays notes and pitches on a timeline.
- **Beat Grid**: Shows drum patterns and hits in a step-sequencer style.
- **Waveform**: A synthetic preview of the song's dynamic envelope.

The **Console** provides real-time feedback from the compiler stages:
- Lexer: Tokenization issues.
- Parser: Structural errors.
- Semantic: Music-domain validation (key compatibility, instrument validity, etc.).

## Project Structure

```text
main.py          # Entry point
compiler/        # DSL Core (Lexer, Parser, Codegen, Music Theory)
gui/             # CustomTkinter Desktop Application
examples/        # Sample .mzt files
outputs/         # Generated MIDI/WAV files
```

## Advanced Logic

The implemented grammar supports:
- **Variables**: Numeric assignments scoped to each `piste`.
- **Expressions**: Arithmetic (`+`, `-`, `*`) and comparisons (`==`, `!=`, `>`, `>=`, `<`, `<=`).
- **Control Flow**: Conditional `si/sinon` blocks for dynamic patterns.

WAV export requires `FluidSynth` to be installed on your system (`brew install fluid-synth` on macOS).