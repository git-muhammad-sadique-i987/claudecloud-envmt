# Hand-off: next version of the F2L Hunting Story video

Context for a new Claude Code session running locally (Windows laptop).

## What exists (v1)
- `f2l_hunting_story.mp4`: 6.6 min, 1280x720, 11 F2L cases (front-right slot), 3D cube,
  algorithm bar at the bottom, on-screen captions only.
- `cube.py` is the cube model; `story.py` holds the script and timeline (`CASES`, `build_timeline`);
  `render.py` renders frames with Pillow and pipes them to ffmpeg.
- Each case is set up by applying the inverse algorithm to a solved cube, so the setup and the
  solution always match. Keep that approach.
- The v1 story ("hunter / prey / den", chapters Pounce, Carry Home, Chase, Looks Up, Trapped)
  is invented, because the cloud session could not open YouTube.

## What the user wants in v2
1. **Voiceover narration** (no TTS was available in the cloud session; Piper TTS is a good offline
   option on Windows, or Windows' built-in SAPI voices).
2. **RiDo's real Hunting Story**: the Crocodile, Tiger and Eagle analogies. Source videos:
   - https://www.youtube.com/watch?v=WB5apB2i_Do (Part 1 of 2; chapters: F2L 7 `U' R U2 R' U2 R U' R'`,
     F2L 10 `U F' U F U' R U R'`)
   - https://www.youtube.com/watch?v=Q2uWq2q3Xoc (Part 2 of 2)
3. **More intuitive teaching, less algorithm memorising**: explain *why* each step works. Copy the
   teaching style of ParadoxCubing, "F2L For Beginners | Easy CFOP Tutorial":
   https://www.youtube.com/watch?v=Hx9ZbPdX8zM (about 29 min; teaches F2L "using only 5 basic cases").
   Algorithms can stay in the bottom bar.
4. Keep the visual style of https://www.youtube.com/watch?v=7L4bB2657WU (current v1 style already matches).

## Suggested first steps locally
- Get the captions and sample frames of the three videos (for example, yt-dlp `--write-auto-subs
  --skip-download`, and low-res frames every few seconds with ffmpeg). Summarise each animal's role
  and the ParadoxCubing structure before changing code.
- Windows tweaks for `render.py`: the font path is `/usr/share/fonts/opentype/inter/`. Point it at an
  installed Inter or Segoe UI font instead. Multiprocessing needs the `if __name__ == "__main__"`
  guard (already present).
- Narration: generate one audio clip per caption, make the timeline holds at least as long as each
  clip, then mux the audio with ffmpeg.
