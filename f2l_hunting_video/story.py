"""The Hunting Story script and the frame-by-frame timeline built from it.

Characters (front-right slot, white cross on the bottom):
  HUNTER = the white corner (white-green-red)
  PREY   = its matching edge (green-red)
  DEN    = the empty slot they belong in
"""
import math

import numpy as np

from cube import Cube, MOVES, invert, parse

CH = {
    1: ("CHAPTER 1 · THE POUNCE", (240, 110, 30)),
    2: ("CHAPTER 2 · CARRY IT HOME", (40, 150, 90)),
    3: ("CHAPTER 3 · THE CHASE", (200, 50, 70)),
    4: ("CHAPTER 4 · THE HUNTER LOOKS UP", (70, 140, 240)),
    5: ("CHAPTER 5 · TRAPPED IN THE DEN", (150, 60, 200)),
}

# (chapter, title, intro caption, [(moves, label, caption), ...])
CASES = [
    (1, "Pounce from the side",
     "The hunter is on the roof, white facing right. The prey waits at the back. "
     "Opening the den will throw the hunter right onto it.",
     [("R", "open den", "Open the den with R. The hunter is lifted up... and lands right on the prey. CAUGHT!"),
      ("U", "walk", "Walk the catch along the roof until it sits above the open den."),
      ("R'", "close den", "Close the den with R'. Hunter and prey are home!")]),
    (1, "Pounce from the front",
     "Mirror image: white faces the front and the prey waits on the left. "
     "Use the front door: F' opens the den from the front.",
     [("F'", "open front door", "F' opens the front door. The hunter swings left... right onto the prey. CAUGHT!"),
      ("U'", "walk", "Walk the catch back over the open den."),
      ("F", "close door", "Close the front door with F. Home!")]),
    (2, "Already caught (right)",
     "The hunter already holds the prey: side by side, colours matching. "
     "Our only job is to carry them home without breaking them apart.",
     [("U", "step away", "Step the pair away first, so opening the den can't tear them apart."),
      ("R", "open den", "Now open the den. The pair waits safely on the roof."),
      ("U'", "line up", "Bring the pair back, right above the open den."),
      ("R'", "close den", "Close the den. Home!")]),
    (2, "Already caught (front)",
     "Same story, mirrored. The pair is ready; this time it goes in through the front door.",
     [("U'", "step away", "Step the pair away from the front door."),
      ("F'", "open door", "Open the front door."),
      ("U", "line up", "Bring the pair back in front of the open door."),
      ("F", "close door", "Close the door. Home!")]),
    (3, "Ambush, then carry",
     "Hunter and prey are apart, so we set an ambush: hide the hunter, "
     "move the prey into place, then spring the trap.",
     [("U' R U R'", "ambush",
       "U' R ducks the hunter down out of sight. U moves the prey. R' springs the hunter back up. CAUGHT!"),
      ("U2 R U' R'", "carry home (ch. 2)",
       "Now it's Chapter 2: U2 steps the pair away, then R U' R' carries it home.")]),
    (3, "Ambush, then pounce",
     "The hunter faces sideways but the prey is in the wrong spot. "
     "Set a trap that turns this into a Chapter 1 pounce.",
     [("U' R U R' U", "set the trap",
       "U' R hides the hunter, U shifts the prey, R' brings the hunter back, and U lines them up."),
      ("R U R'", "pounce (ch. 1)",
       "Chapter 1! Open the den, the hunter lands on the prey, walk, close. Home!")]),
    (4, "Looking up, prey on the right",
     "The hunter's white face looks at the sky, so it can't see the prey. "
     "First turn it to look sideways.",
     [("R U2 R'", "turn the hunter",
       "Hide the hunter in the den (R), spin the roof (U2), bring it back out (R'). Now white faces sideways."),
      ("U'", "line up", "Line up for the pounce."),
      ("R U R'", "pounce (ch. 1)", "Chapter 1 pounce. Home!")]),
    (4, "Looking up, prey at the back",
     "White looks up again and the prey is behind it. This time "
     "turning the hunter around catches the prey for us.",
     [("U R U2 R'", "turn & catch",
       "Step aside (U), open the den (R), spin the roof (U2): CAUGHT! Then close the den (R')."),
      ("U R U' R'", "carry home (ch. 2)", "Chapter 2: step away, open, line up, close. Home!")]),
    (5, "Hunter trapped in the den",
     "The hunter is sitting in the den, but the prey is outside. "
     "Kick the hunter out so it can grab the prey.",
     [("U R U' R'", "kick it out",
       "Move the prey aside (U), open the den (R), step away (U'), close (R'). The hunter pops out holding the prey. CAUGHT!"),
      ("U' F' U F", "carry home (ch. 2)", "Chapter 2 through the front door. Home!")]),
    (5, "Hunter trapped, white facing front",
     "Trapped again, and twisted the wrong way: white faces the front. Pull it out and catch the prey on the way.",
     [("R U' R'", "pull it out",
       "Open the den: the hunter comes up (R). Slide the roof (U'): CAUGHT! Close the den (R')."),
      ("U R U' R'", "carry home (ch. 2)", "Chapter 2. Home!")]),
    (5, "Prey trapped in the den",
     "Now the PREY is stuck in the den and the hunter is looking up. "
     "Swap them, turn the hunter, then pounce.",
     [("R U R' U'", "swap", "Swap places: the prey escapes the den and the hunter jumps in."),
      ("R U R' U'", "climb out", "Same moves again: the hunter climbs back out, now facing sideways."),
      ("R U R'", "pounce (ch. 1)", "Chapter 1 pounce. Home!")]),
]

HUNTER, PREY = (1, -1, 1), (1, 0, 1)


class Builder:
    def __init__(self, fps):
        self.fps = fps
        self.frames = []
        self.cube = Cube()
        self.pop = None  # (text, start_frame, frames, colour)

    # -- state helpers
    def piece(self, home):
        return self.cube.find(home)

    def paired(self):
        co, ed = self.piece(HUNTER), self.piece(PREY)
        if np.abs(co.pos - ed.pos).sum() != 1:
            return False
        return all(np.allclose(co.M @ n, ed.M @ n) for n, _ in ed.stickers)

    def home(self):
        return all(np.allclose(self.piece(h).M, np.eye(3)) for h in (HUNTER, PREY))

    def den_empty(self):
        return all(round(self.piece(h).pos[1]) == 1 for h in (HUNTER, PREY))

    # -- emitting frames
    def emit(self, base, anim=None):
        fr = dict(base)
        fr["state"] = self.cube.snapshot()
        fr["anim"] = anim
        if self.pop:
            txt, start, n, col = self.pop
            k = len(self.frames) - start
            if k < n:
                fr["pop"] = (txt, k / n, col)
            else:
                self.pop = None
        self.frames.append(fr)

    def hold(self, base, seconds):
        for _ in range(int(seconds * self.fps)):
            self.emit(base)

    def move(self, base, token, seconds=0.6, pause=0.2, pops=True):
        b, n, _ = parse(token)[0]
        axis = MOVES[b][0]
        idxs = [self.cube.cubies.index(c) for c in self.cube.layer(b)]
        total = self.cube.angle(b, n)
        nf = max(2, int(seconds * self.fps * (1.35 if abs(n) == 2 else 1)))
        was_paired = self.paired()
        for k in range(nf):
            t = k / nf
            e = 0.5 - 0.5 * math.cos(math.pi * t)
            self.emit(base, (idxs, axis, total * e))
        self.cube.apply(b, n)
        if pops:
            if self.home():
                self.pop = ("HOME!", len(self.frames), int(1.6 * self.fps), (120, 255, 150))
            elif self.paired() and not was_paired:
                self.pop = ("CAUGHT!", len(self.frames), int(1.3 * self.fps), (255, 205, 0))
        self.hold(base, pause)


def read_time(text):
    return max(2.4, 0.3 * len(text.split()) + 0.8)


def build_timeline(fps=30):
    B = Builder(fps)

    # ---- title: slowly spinning solved cube
    n = int(5 * fps)
    for k in range(n):
        B.emit(dict(kind="title", yaw=-38 + 50 * math.sin(2 * math.pi * k / n) * 0.5,
                    cube_xy=(900, 370), cube_scale=125, glow=False))

    # ---- meet the characters (setup of the first case)
    B.cube = Cube().run(invert("R U R'"))
    base = dict(kind="intro", chip="MEET THE CHARACTERS", chip_color=(150, 60, 200),
                title="Who's who?", tags=True, den_tag=True)
    for cap in ["The HUNTER is the white corner: white, green and red.",
                "The PREY is the edge that matches it: green and red.",
                "The DEN is the empty slot where they both belong: between the green and red centres.",
                "Goal of every story: the hunter CATCHES the prey (a pair), then carries it HOME into the den."]:
        B.hold(dict(base, caption=cap), read_time(cap))

    # ---- the rules of the hunt, demonstrated on a solved F2L
    B.cube = Cube()
    rules = [
        ("R", "Open the den.", "R lifts the den up onto the roof."),
        ("R'", "Close the den.", "R' puts it back down."),
        ("F'", "Front door.", "F' opens the den from the front; F closes it."),
        ("F", None, None),
        ("U", "Walk on the roof.", "U moves never disturb pieces already home in the bottom two layers."),
        ("U'", None, None),
    ]
    shown = []
    for tok, head, body in rules:
        if head:
            shown.append((head, body))
        fr = dict(kind="rules", chip="THE RULES OF THE HUNT", chip_color=(150, 60, 200),
                  title="How the hunt works", bullets=list(shown), bullets_y=170, glow=False,
                  speed_label=f"move: {tok}")
        B.hold(fr, 1.6 if head else 0.3)
        B.move(fr, tok, seconds=0.8, pause=0.6, pops=False)
    shown.append(("Catch, then carry.", "Hunter + prey side by side with matching colours = CAUGHT. "
                                        "Then carry the pair into the den."))
    B.hold(dict(fr, bullets=list(shown), speed_label=None), 4.5)

    # ---- the cases
    for ci, (chap, title, intro, chunks) in enumerate(CASES, 1):
        alg = " ".join(m for m, _, _ in chunks)
        setup = Cube().run(invert(alg))
        B.cube = setup
        tokens = alg.split()
        spans, start = [], 0
        for m, label, _ in chunks:
            spans.append((start, len(m.split()), label))
            start += len(m.split())
        chip, col = CH[chap]
        base = dict(kind="case", chip=chip, chip_color=col, title=title,
                    subtitle=f"Case {ci} of {len(CASES)}   ·   {alg}",
                    tags=True, alg_tokens=tokens, alg_chunks=spans, alg_cur=-1, alg_done=0)

        B.hold(dict(base, caption=intro, den_tag=B.den_empty()), read_time(intro) + 0.6)
        done = 0
        for k, (m, label, cap) in enumerate(chunks):
            fr = dict(base, caption=cap, chunk_hint=k, alg_done=done)
            B.hold(fr, read_time(cap) * 0.7)
            for tok in m.split():
                B.move(dict(fr, alg_cur=done, alg_done=done), tok)
                done += 1
            B.hold(dict(fr, alg_done=done), 0.9)
        B.hold(dict(base, caption=f"Home! The whole story: {alg}", alg_done=done), 2.4)

        # replay at solving speed
        B.cube = Cube().run(invert(alg))
        rb = dict(base, caption="Again at solving speed. Say the story in your head as you turn.",
                  speed_label="REPLAY · FAST")
        B.hold(rb, 1.6)
        for i, tok in enumerate(tokens):
            B.move(dict(rb, alg_cur=i, alg_done=i), tok, seconds=0.3, pause=0.06, pops=False)
        B.hold(dict(rb, alg_done=len(tokens)), 1.2)

    # ---- recap
    table = [
        ("1 · The Pounce", "R U R'", "Open the den, the hunter lands on the prey, walk, close."),
        ("2 · Carry It Home", "U R U' R'", "Already caught: step away, open, line up, close."),
        ("3 · The Chase", "U' R U R'  →  ch. 1 or 2", "Ambush first, then pounce or carry."),
        ("4 · Hunter Looks Up", "R U2 R'  →  ch. 1 or 2", "Turn the hunter to face sideways first."),
        ("5 · Trapped in the Den", "R U' R'  /  U R U' R'  →  ch. 1 or 2", "Get it out of the den first, then pounce or carry."),
    ]
    B.cube = Cube()
    B.hold(dict(kind="outro", show_cube=False, chip="STORY RECAP", chip_color=(150, 60, 200),
                title="The whole hunt in 5 chapters", table=table,
                footer="Front-door mirror: swap R → F', R' → F and U ↔ U'."), 12)
    return B.frames
