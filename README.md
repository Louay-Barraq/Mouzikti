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

- Run: compile current editor content
- Export MIDI: save generated MIDI to chosen location
- Export WAV: visible but currently disabled (planned feature)
- Save/Open: .mzt file operations

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

- piste
- batterie
- mélodie / melodie
- basse
- mesure
- note
- accord
- tempo
- tonalité / tonalite
- durée / duree
- instrument
- effets
- répéter / repeter
- suivre
- racine
- rythme
- volume
- reverb
- swing
- echo
- oui
- non

## Supported Durations

- ronde
- blanche
- noire
- croche
- double_croche

## Supported Instruments

- piano
- guitare
- basse_électrique / basse_electrique
- violon
- flûte / flute
- orgue
- synthé / synthe

## Supported Drum Voices

- kick
- snare
- hihat
- clap
- tom
- crash

## Error Reporting

Mouzikti reports errors by stage:

- Lexer: illegal characters and tokenization issues
- Parser: unexpected token or missing structure
- Semantic: music-domain validation (instrument validity, scale checks, effects range, etc.)

Compiler messages are emitted as structured CompilerMessage entries and displayed in the GUI console.

## Project Structure

```text
main.py
compiler/
gui/
examples/
output/
docs/
```

## Current Scope Notes

The implemented grammar supports tracks, battery, melody, bass, effects, repeat blocks,
numeric variable assignments, arithmetic expressions (+, -, *), and si/sinon branching with boolean
or numeric comparison conditions (==, !=, >, >=, <, <=).

Some advanced PRD roadmap items remain optional/planned, such as WAV conversion backend and waveform visualization.