# F2L Hunting Story: narrated 3D animated video

`f2l_hunting_story_v5.mp4` (1280x720, voiceover by a calm cubing coach) teaches intuitive F2L
(front-right slot) with RiDo's Hunting Story, in the shape of ParadoxCubing's "F2L For Beginners":
the five basic cases, what to do when the prey is in the wrong spot, then how to free stuck pieces. See
`RESEARCH_NOTES.md` for the sources and what changed in each version.

- **Hunter** = white corner, **Prey** = matching edge, **Den** = the empty slot
- 🐅 **Tiger** (different top colours): jump, drag back, home: `R U R'`, mirror `F' U' F`
- 🐊 **Crocodile** (same top colours): hide, the prey walks over, strike, then home:
  `U' R U R' U2 R U' R'`, mirror `U F' U' F U2 F' U F`
- 🦅 **Eagle** (white on top): line up, drop the prey, fly over, grab, then home: `U R U2 R' U R U' R'`
- **Prey in the wrong spot**: the hunter hides, the prey walks into its **kill zone**, and the hunter comes
  back. Tiger with the prey on the left: `U F' U F U' R U R'` (hide, line the prey up with its centre, come
  back, pounce). Crocodile with the prey further away: `U' R U2 R' U2 R U' R'` (only the walk is longer).
  Already touching with matching colours: just take it home (`U R U' R'`).
- **Stuck pieces**: lift, step clear, put the face back, so it comes up as a tiger (6-7 moves each)
- Three rules: the top layer turns freely; a side face goes a quarter turn out and straight back; the golden
  rule (only lift the empty den). Every solve is the shortest one that keeps these rules, so the other
  three slots are never broken.

Each case: **try it yourself** (the set-up moves build the case on a solved cube, in a blue bar marked "not the
solution"), **spot it** (bullets), **solve it** (numbered steps in sync with the move bar), **why it works**,
and a replay at full speed. Every case is set up by applying the inverse solve to a solved cube, so the shown
state and the solution always match.

Files for YouTube:
- `f2l_hunting_story_v5.mp4`: the video
- `f2l_hunting_story_v5.srt`: closed captions of the narration
- `f2l_hunting_story_v5_thumbnail.png`: thumbnail
- `youtube_description.txt`: title, description, set-up moves, chapter timestamps and credits

`f2l_hunting_story_v4.mp4` (basic cases only), `f2l_hunting_story_v3.mp4` (Kokoro voice, follow-along
scrambles), `f2l_hunting_story_v2.mp4` (12 cases, Piper voice) and `f2l_hunting_story.mp4` (v1, captions only)
are the earlier versions.

## Rebuild (Windows)

Needs Python with numpy and Pillow, and ffmpeg on PATH. The voice is Microsoft Edge's `en-GB-RyanNeural`
(`pip install edge-tts`, needs an internet connection, no account or key):

```
set EDGE_VOICE=en-GB-RyanNeural
set NARRATION_SPEED=0.9
python render.py f2l_hunting_story_v5.mp4
python render.py --thumbnail f2l_hunting_story_v5_thumbnail.png
```

Other voices (see `narrate.py`; the first one whose setting is present is used):
- **ElevenLabs**: `ELEVENLABS_KEY_FILE` = a text file holding your API key (keep it outside the repo),
  `ELEVENLABS_VOICE` = voice id. Each line is voiced with its neighbouring lines as context.
- **Kokoro** (offline, slow on a CPU): `KOKORO_MODEL`, `KOKORO_VOICES` and `KOKORO_VOICE`, with the model files
  from https://github.com/thewh1teagle/kokoro-onnx/releases (model-files-v1.0) and `pip install kokoro-onnx`.
- **Piper**: `PIPER_VOICE`; otherwise the Windows SAPI voice.

Clips are cached in `narration_cache/`, so later builds only voice changed lines. `NARRATION_SPEED` sets the
pace (1.0 = the voice's normal speed). Set `NARRATION=0` for a silent build, and use `--preview N` to render
every Nth frame.

Edit the script and cases in `story.py`. In spoken lines:
- `|` splits a line into parts with a short pause between them
- `^` marks where the move on screen starts
- `**word**` highlights a word on screen
- `!` is shown on screen but read as `.`, so the voice stays calm
