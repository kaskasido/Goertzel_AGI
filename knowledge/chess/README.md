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
| `00_relations.nico` | Relation vocabulary — defines which questions become askable |
| `01_board.nico` | Board structure: 8×8 grid, ranks, files, square colors, starting zones |
| `02_pieces.nico` | Piece taxonomy, count per side, starting squares, relative values |
| `03_moves.nico` | Movement rules for every piece; castling, en passant, promotion |

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
