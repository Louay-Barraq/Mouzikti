# Mouzikti Grammar (Implemented Subset)

This file documents the grammar currently implemented by compiler/parser.py.

## EBNF

```ebnf
program         = track_list ;

track_list      = track , { track } ;

track           = "piste" , STRING , "{" , track_body , "}" ;
track_body      = track_attr_list , layer_list ;

track_attr_list = { track_attr } ;
track_attr      = tempo_attr | tonalite_attr | duree_attr | variable_assign ;

tempo_attr      = "tempo" , ":" , BPM ;
tonalite_attr   = "tonalité" , ":" , STRING
								| "tonalite" , ":" , STRING ;
duree_attr      = "durée" , ":" , MESURES
								| "duree" , ":" , MESURES ;
variable_assign = IDENTIFIER , "=" , number_val ;

layer_list      = { layer } ;
layer           = battery_block | melody_block | bass_block ;

battery_block   = "batterie" , "{" , battery_body , "}" ;
battery_body    = mesure_block , battery_opts ;
mesure_block    = "mesure" , "{" , beat_row_list , "}" ;

beat_row_list   = beat_row , { beat_row } ;
beat_row        = IDENTIFIER , ":" , "[" , beat_steps , "]" ;
beat_steps      = beat_step , { beat_step } ;
beat_step       = "X" | "." ;

battery_opts    = [ effects_block ] , [ repeat_stmt ] ;
repeat_stmt     = "répéter" , NUMBER
								| "repeter" , NUMBER ;

melody_block    = ( "mélodie" | "melodie" ) , "instrument" , ":" , IDENTIFIER ,
									"{" , melody_body , "}" ;
melody_body     = measure_list , [ effects_block ] ;
measure_list    = measure_block_melody , { measure_block_melody } ;

measure_block_melody
								= "mesure" , NUMBER , ".." , NUMBER , "{" , stmt_list , "}"
								| "mesure" , NUMBER , "{" , stmt_list , "}" ;

stmt_list       = { stmt } ;
stmt            = note_stmt | accord_stmt | repeat_block_stmt | if_stmt ;

note_stmt       = "note" , "(" , NOTE_NAME , "," , DURATION , ")" ;
accord_stmt     = "accord" , "(" , CHORD_NAME , "," , DURATION , ")" ;
repeat_block_stmt
								= ( "répéter" | "repeter" ) , NUMBER , "{" , stmt_list , "}" ;
if_stmt         = "si" , bool_expr , "{" , stmt_list , "}"
                | "si" , bool_expr , "{" , stmt_list , "}" , "sinon" , "{" , stmt_list , "}" ;

bass_block      = "basse" , "instrument" , ":" , IDENTIFIER , "{" , bass_body , "}" ;
bass_body       = follow_with_rythme
								| follow_only
								| rythme_only ;

follow_with_rythme
								= "suivre" , IDENTIFIER , "racine" , ":" , "oui" ,
									"rythme" , ":" , "[" , beat_steps , "]" ;
follow_only     = "suivre" , IDENTIFIER , "racine" , ":" , "oui" ;
rythme_only     = "rythme" , ":" , "[" , beat_steps , "]" ;

effects_block   = "effets" , "{" , effect_list , "}" ;
effect_list     = effect_item , { "," , effect_item } ;
effect_item     = "reverb" , ":" , number_val
								| "echo"   , ":" , number_val
								| "volume" , ":" , number_val
								| "swing"  , ":" , number_val ;

number_val      = number_expr ;
number_expr     = FLOAT
				| NUMBER
				| IDENTIFIER
				| "(" , number_expr , ")"
				| number_expr , "+" , number_expr
				| number_expr , "-" , number_expr
				| number_expr , "*" , number_expr ;

bool_expr       = bool_literal
				| "(" , bool_expr , ")"
				| number_expr
				| number_expr , "==" , number_expr
				| number_expr , "!=" , number_expr
				| number_expr , ">"  , number_expr
				| number_expr , ">=" , number_expr
				| number_expr , "<"  , number_expr
				| number_expr , "<=" , number_expr ;
bool_literal    = "oui" | "non" ;
```

## Lexical Tokens (high level)

- **Literals**: `NUMBER`, `FLOAT`, `STRING`, `NOTE_NAME`, `CHORD_NAME`, `IDENTIFIER`
- **Units**: `BPM` (e.g., `120bpm`), `MESURES` (e.g., `8_mesures`)
- **Rhythm tokens**: `X` (BEAT_X), `.` (BEAT_DOT)
- **Delimiters/Operators**: `{`, `}`, `[`, `]`, `(`, `)`, `:`, `,`, `=`, `..`
- **Arithmetic**: `+`, `-`, `*`
- **Comparisons**: `==`, `!=`, `>`, `>=`, `<`, `<=`
- **Keywords**:
  - Structure: `piste`, `batterie`, `mélodie`/`melodie`, `basse`, `mesure`
  - Content: `note`, `accord`, `tempo`, `tonalité`/`tonalite`, `durée`/`duree`, `instrument`, `effets`
  - Logic: `répéter`/`repeter`, `si`, `sinon`, `oui`, `non`
  - Bass/Rhythm: `suivre`, `racine`, `rythme`
  - Effects: `volume`, `reverb`, `swing`, `echo`
- **Durations**: `ronde`, `blanche`, `noire`, `croche`, `double_croche`, `triple_croche`, `blanche_pointée`, `noire_pointée`, `croche_pointée`

## Notes

- **Conditionals**: `si/sinon` blocks allow for basic logic based on numeric comparisons or boolean literals (`oui`/`non`).
- **Variable Scoping**: Variables assigned with `IDENTIFIER = number_val` are local to the current `piste` block and can be used in arithmetic or conditions.
- **Rhythmic Patterns**: Drums and Bass layers use a 16-step grid by default where `X` represents a hit and `.` represents a rest.
- **Bass Follow**: The `suivre` keyword in the `basse` block enables automatic root-note tracking based on chords played in the `mélodie` layers.
