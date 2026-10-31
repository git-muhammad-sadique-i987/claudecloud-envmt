# F2L Hunting Story — 3D animated video

`f2l_hunting_story.mp4` (6.6 min, 1280x720) teaches 11 intuitive F2L cases (front-right slot) as a story:

- **Hunter** = white corner, **Prey** = matching edge, **Den** = the empty slot
- Ch.1 The Pounce (`R U R'`), Ch.2 Carry It Home (`U R U' R'`), Ch.3 The Chase,
  Ch.4 The Hunter Looks Up, Ch.5 Trapped in the Den — later chapters reuse earlier ones.

Each case shows the story step by step, then replays at solving speed.
Every case is set up by applying the inverse algorithm to a solved cube, so the
shown state and solution always match.

Rebuild: `python3 render.py f2l_hunting_story.mp4` (needs numpy, Pillow, ffmpeg, Inter font).
Edit the story / cases in `story.py`.
