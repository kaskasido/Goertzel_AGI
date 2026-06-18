# Chess knowledge pack

A knowledge pack that teaches the AGI everything it needs to know about chess:
what chess is, how the board is set up, what pieces exist, and the movement
rules for every piece (including special moves). No opening theory or tactics —
just the pure rules.

## Load it

```bash
python -m goertzel_agi.teach knowledge/chess
```

Or drop the files into `inbox/` and click **Process inbox** in the web UI.

## Files

| File | Content |
|---|---|
| `00_relations.alex` | Relation vocabulary — defines which questions become askable |
| `01_board.alex` | Board structure: 8×8 grid, ranks, files, square colors, starting zones |
| `02_pieces.alex` | Piece taxonomy, count per side, starting squares, relative values |
| `03_moves.alex` | Movement rules for every piece; castling, en passant, promotion |

## Things to ask afterwards

**Is-a / taxonomy (Subject → Object):**
- `chess` → `board_game` ✓
- `the_knight` → `chess_piece` ✓
- `en_passant` → `special_move` ✓

**Relation questions (Subject + relation):**
- `the_queen` + `can_move_like` → *any direction, unlimited squares*
- `the_knight` + `can_capture_like` → *L-shape*
- `the_king` + `has_count` → *one per side*
- `castling` + `shows` → all conditions for a legal castle
- `chess` + `wins_by` → *checkmating the opponent king*
- `the_pawn` + `can_move_like` → *one square forward*

## Coverage

- ♔ King — one square any direction, castling
- ♕ Queen — any direction, unlimited squares
- ♖ Rook — horizontal/vertical, unlimited squares
- ♗ Bishop — diagonal, unlimited squares
- ♘ Knight — L-shape, jumps over pieces
- ♙ Pawn — forward move, diagonal capture, en passant, promotion
- Draw conditions: stalemate, insufficient material, threefold repetition, fifty-move rule

## Gespeicherte Partien einbinden

Alex hat auf einer Online-Plattform (z. B. **Lichess** oder **Chess.com**)
Partien gespielt, die gespeichert sind. Diese Partien sind wichtiges Material
um zu verstehen, **wie sein Bruder gespielt hat** — welche Eröffnungen er
bevorzugt hat, wie er Mittelspiele geführt hat, welche taktischen Muster er
immer wieder eingesetzt hat.

### Partien exportieren

**Lichess:**
```
https://lichess.org/@/<benutzername>/games/export
```
Format wählen: **PGN** (Portable Game Notation) — das ist das Standard-Format
für Schachpartien.

**Chess.com:**
Im Profil → *Game Archive* → *Export*

### Partien in die AGI einbringen

PGN-Dateien sind strukturierter Text. Die Züge (z. B. `1. e4 e5 2. Nf3 Nc6`)
können als Satz-Tripel in eine `.alex`-Datei übersetzt werden, zum Beispiel:

```
# Aus Partie 1 — Eröffnung
alex_bruder prefers_opening kings_pawn_e4
alex_bruder plays_after_e4 nf3_attack
alex_bruder avoids sicilian_defense
```

Oder man legt die rohen PGN-Dateien in `inbox/` und schreibt einen
Konverter (`pgn_to_alex.py`), der aus den Zügen Muster-Tripel erzeugt.

### Ziel

Aus den gespeicherten Partien soll die AGI lernen:
- Welche Eröffnungen wurden bevorzugt?
- Welche Figuren wurden früh aktiviert?
- Gab es Lieblingsmuster (Gabeln, Fesselungen, Opfer)?
- Wie war der typische Spielrhythmus — aggressiv, positionell, defensiv?

So entsteht ein **symbolisches Profil des Spielstils** — etwas, das Alex
für sich selbst versteht.
