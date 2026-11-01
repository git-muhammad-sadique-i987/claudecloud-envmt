# Research notes for v2

Sources: the English captions of RiDo's two-part "Hunting Story for F2L" (WB5apB2i_Do, Q2uWq2q3Xoc),
the transcript of ParadoxCubing's "F2L For Beginners | Easy CFOP Tutorial" (Hx9ZbPdX8zM), and sample
frames of each.

## RiDo's Hunting Story

**Terms.** The corner is the **hunter** (predator) and the matching edge is the **prey** (victim). When they
join perfectly, that is a **kill**. The **kill zone** is the spot where the prey must be for the next move
to join them.

**Working range (rules).**
- White cross on the bottom. The top layer can turn freely.
- A side face only turns +90° and then back -90°. No half turns, and no other side face moves until it is
  restored. The bottom layer never moves.
- Before hunting, both pieces must be on the top layer and apart from each other.

**Line of action.** A hunter can only move (hide or hunt) by turning the face its white sticker is on.
RiDo says this applies only while hiding or hunting, not while adjusting pieces.

**Hiding place.** Before hiding, spin the top layer until the slot diagonal to the white sticker, which is
the one the turn will lift, is unsolved. ParadoxCubing calls this the golden rule.

**The three hunters** (pieces on top, apart):

| Hunter | Recognition | How it hunts | ParadoxCubing name |
|---|---|---|---|
| Crocodile | top colours of corner and edge are the **same** | Hides under water (side face turn), waits while the prey walks on the land (U) into the kill zone, then rises: kill. Then the **garage**: make the L, pull the white away (U), open the garage door, drive in, close it. | matching case |
| Tiger | top colours are **opposite**, like stripes | Chases first if needed (hide, move the prey, unhide), then goes to its **den / base location** (above its slot), **jumps** onto the prey (`R`), **drags it back** (`U`) and **enters the cave** (`R'`). | non-matching case |
| Eagle | the corner's **white sticker faces up** (the edge can face either way) | Line the edge's side colour up with its centre (a vertical line), turn that face **away** from the edge's top colour (the line goes horizontal and the prey drops to the land), the eagle **flies** in the sky (U) until it is above the prey, turn the face back: kill. Then the garage. | white-on-top case |

**Part 2 extras.**
- *Pieces not on top*: turn any face that lifts the piece, then turn U so that neither piece sits on the
  restoring face, then restore. Smart version: lift it the way that makes it a **tiger already in the
  kill zone** ("let us go for the tiger always").
- *Bad joint*: split it like "a slice of bread from a loaf". Turn the one face that can still turn, hide,
  move U away, restore. Sometimes this turns a bad joint into a kill-zone tiger in 3 moves.
- The video closes with a puzzle: which hunter does the beginner's-method edge insert use?

## ParadoxCubing's teaching structure

1. **Intro**: what F2L is (pair a corner and an edge, insert the pair; 4 slots), and why you need
   only 5 basic cases instead of about 40 algorithms. "Treat this video as a reference". Gives a breakdown of the
   parts.
2. **Part 1, convert any case into a basic one** with a 3-step process: corner to the top layer, edge
   to the top layer, split them apart (the **hiding trick**).
3. **Part 2, the 5 basic cases**: matching, non-matching, white on top, mirrored matching and mirrored
   non-matching. For each case: how to recognise it, preconditions ("the edge must be at the back"),
   the solve, and *why* each move works ("this fixes the cross and inserts the pair at the same time").
4. **Part 3, the golden rule**: the slot you lift when hiding must be unsolved.
5. **Part 4, a worked example**, then next steps.

Tone: encouraging ("don't worry if it doesn't click right away"), with recognition before the solve and an
explanation after it.

## How v2 combines them

- RiDo's story and words (crocodile, tiger, eagle, den, kill zone, garage, cave, line of action, slice of
  bread) set in ParadoxCubing's order: intro and plan, rules, recognising the hunters, the basic
  cases with their mirrors, converting stuck cases, then a recap.
- Each case: recognition caption plus a checklist, then step-by-step narrated moves, then a **why it works**
  caption, then a replay at solving speed.
- Every case is still set up by applying the inverse algorithm to a solved cube.

## v3 changes (after viewer feedback)

- **Fewer moves**: ParadoxCubing's five basic cases only (81 moves across 12 cases in v2, now 30 across 5),
  plus three stuck-piece fixes of 6-7 moves. A search over all move sequences that keep the rules (side face
  out a quarter turn and straight back, top layer free) confirmed each solve is the shortest possible: tigers
  3 moves, crocodiles and the eagle 8. ParadoxCubing's 7-move matching solve (`R' U2 R` + insert) lifts the
  back slot, which is fine for a first pair but breaks a solved back slot, so the video keeps the golden-rule
  version.
- **Easiest first**: the tiger (3 moves) opens the cases, then the crocodile, then the eagle.
- **Human narration**: a friendly cubing coach, written as short spoken phrases with pauses, reactions and
  questions, voiced with Kokoro (`bm_george`).
- **Structured text**: bullet cards (spot it / solve it / why it works) instead of paragraphs, with key words
  highlighted; the full narration is in the `.srt` captions.
- **YouTube extras**: follow-along scrambles, chapter timestamps and a description, and a thumbnail.

## v4 changes (after viewer feedback on v3)

- **Set-up moves are not the solution**: v3 showed a "follow-along scramble" next to the solve, and it read
  like the solving algorithm. Each case now opens with its own **Try it yourself** step: the cube starts
  solved, the set-up moves play in a blue bar labelled "set-up moves · not the solution", the subtitle says
  they only build the case, and the narrator suggests pausing to try it. During the solve the subtitle just
  says how many moves it takes. The description lists every case's set-up moves with the same warning.
- **Calmer, more human narration**: no Claude or community "skill" humanizes a TTS voice; the ones found
  either polish a script or call a paid voice API. So the script was rewritten in a calm coaching voice (full
  sentences of varied length, no exclamations, `!` stays on screen only) and each line is voiced whole instead
  of in short phrases, which gave v3 its fixed rhythm. The pace dropped from about 170 words/min (v3) to
  about 155. Voice: Microsoft Edge neural voice `en-GB-RyanNeural` via the `edge-tts` package at speed 0.9,
  picked from samples of Andrew, Brian, Ryan and Ava. An ElevenLabs engine (model `eleven_v4`, each line
  voiced with its neighbours as context) is ready for a later version.
- **Moves in sync with the voice**: a `^` in a spoken line marks where the move starts, and the cube turns
  there instead of after the whole line.
- **Labels on the right pieces**: HUNTER and PREY pointed at the centre of the piece, which is inside the
  cube, so on screen the dot often landed on a neighbouring sticker. They now point at the piece's own sticker
  (the hunter's white sticker when visible, the prey's top sticker), spread apart when they would overlap, and
  stay on screen and clear of the text card. All 88 labelled cube states were checked.
- **Credit to RiDo**: the thumbnail reads "F2L HUNTING STORY" with "Based on RiDo's Hunting Story", the title
  card credits RiDo and ParadoxCubing, the YouTube title starts with "F2L Hunting Story", and the description
  opens with RiDo's credit and links to both parts.
