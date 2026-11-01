"""The Hunting Story (v4) script and the frame-by-frame timeline built from it.

RiDo's "Hunting Story for F2L" told by a friendly cubing coach, in the shape of ParadoxCubing's
"F2L For Beginners": the five basic cases (each in the fewest moves that never lift a solved slot),
then how to get stuck pieces out, then a recap.

Characters (front-right slot, white cross on the bottom, green front, yellow top):
  HUNTER = the white corner (white-green-red); it is a CROCODILE, TIGER or EAGLE
  PREY   = its matching edge (green-red)
  DEN    = the empty slot they belong in
  TIGER     = top colours differ (non-matching)   CROCODILE = top colours match (matching)
  EAGLE     = the hunter's white sticker faces up (white on top)

Spoken lines are voiced whole, so the voice keeps a natural flow; "|" splits a line into separately voiced
parts with a beat between them, and "^" marks the word the move starts on. The script is written to be
said calmly: full sentences, no exclamation marks. On-screen text is short bullets; **word** is highlighted.
"""
import math
import os

import numpy as np

from cube import Cube, MOVES, invert, parse

CROC, TIGER, EAGLE = "\U0001F40A", "\U0001F405", "\U0001F985"
PURPLE = (150, 60, 200)
ORANGE, GREEN, BLUE = (240, 110, 30), (40, 150, 90), (70, 140, 240)
SLATE = (80, 110, 175)

# A case: chapter, animal, title, set-up lines, spot (bullets + lines), steps, why, replay line.
# steps: (moves, bar label, bullet, spoken line with ^ on the move[, pop])
CASES = [
    dict(chapter="Tiger", color=ORANGE, animal=(TIGER, "TIGER"), title="The tiger pounces", alg="R U R'",
         setup=["If you'd like to follow along, start with a solved cube. Yellow on top, and green facing you.",
                "Then do these set-up moves. They aren't the solution, they just build the case for you.",
                "So pause the video, and see if you can solve it before I do."],
         spot=[((TIGER, "Top colours **different**: tiger"),
                "Let's start with the easiest one. Look at the top. There's red on the hunter, and green on the "
                "prey. They're different, so this is a tiger."),
               (("•", "Hunter sits right **above its den**"),
                "A tiger always hunts from its den. It's sitting right above the empty slot,"),
               (("•", "Prey waits **right behind** it"), "and its prey is waiting just behind it.")],
         steps=[("R", "jump", "**Jump** onto the prey", "Watch the tiger. It jumps onto its prey, ^R,"),
                ("U", "drag back", "**Drag** it back over the den", "drags it back over the den, ^U,"),
                ("R'", "home", "Take it **home**", "and takes it home. ^R prime.")],
         why=[(("•", "R swings the hunter to the **back**"),
               "So why does that work? Well, R swings the hunter round to the back,"),
              (("•", "...right where the prey **waits**"),
               "right where the prey is waiting. That's why the prey has to sit behind it.")],
         replay="Here it is again, at full speed.", after="Three moves. That's all it takes."),
    dict(chapter=None, color=ORANGE, animal=(TIGER, "TIGER"), title="Tiger at the front door", alg="F' U' F",
         setup=["Here's the set-up for the mirror version."],
         spot=[((TIGER, "Top colours **different**: tiger"),
                "This is the same tiger, mirrored. The top colours are different, so it's still a tiger."),
               (("•", "White faces the **front**"), "But this time, its white sticker faces the front,"),
               (("•", "Prey waits on the **left**"), "so the prey is waiting over on the left.")],
         steps=[("F'", "jump", "**Jump** with the front face", "It jumps with the front face this time. ^F prime."),
                ("U'", "drag back", "**Drag** it back", "Drags it back, ^U prime,"),
                ("F", "home", "Take it **home**", "and home. ^F.")],
         why=[(("•", "Mirror: **R → F'** and **U → U'**"),
               "Do you see the pattern? Every R becomes F prime, and the U turns go the other way."),
              (("•", "Learn one side, get the other **free**"),
               "So once you've learned one side, you get the other one for free.")]),

    dict(chapter="Crocodile", color=GREEN, animal=(CROC, "CROCODILE"), title="The crocodile waits",
         alg="U' R U R' U2 R U' R'",
         setup=["Set this one up, and have a go before I show you."],
         spot=[((CROC, "Top colours **the same**: crocodile"),
                "Now, this one's a bit different. There's green on top of the hunter, and green on top of the "
                "prey. Same colour, so it's a crocodile."),
               (("•", "Crocodiles don't chase: they **hide** and **wait**"),
                "And crocodiles don't chase. They hide under the water, and wait for the prey to come to them.")],
         steps=[("U'", "get ready", "Spin so the white faces **right**",
                 "First, turn the top so the white sticker faces right. ^U prime."),
                ("R", "dive", "**Dive!** The empty den comes up",
                 "Now it dives under, ^R. And notice, it's the empty den that comes up, so nothing gets broken."),
                ("U", "prey walks", "The prey **walks over** it",
                 "The prey walks right over the hidden crocodile. ^U."),
                ("R'", "strike", "**Strike!**", "And then, it strikes. ^R prime."),
                ("U2", "swing away", "Swing the pair **away**",
                 "Now we take it home. Swing the pair away from the den first. ^U two."),
                ("R U' R'", "home", "**Open**, slide in, **close**",
                 "Then open the den, ^R, slide it in, U prime, and close it, R prime.")],
         why=[(("•", "A hidden piece is **safe** from U turns"),
               "Here's the big idea. While the crocodile's hidden, turning the top can't touch it."),
              (("•", "So the prey can walk **right next to it**"),
               "So you can walk the prey exactly where you want it, and then bring the hunter back up beside it.")],
         replay="Full speed now. Hide, wait, strike, and home."),
    dict(chapter=None, color=GREEN, animal=(CROC, "CROCODILE"), title="Crocodile at the front door",
         alg="U F' U' F U2 F' U F",
         setup=["The set-up moves are on screen, as always."],
         spot=[((CROC, "Top colours **the same**: crocodile"), "Red on top, and red on top. Another crocodile."),
               (("•", "This one dives through the **front** door"),
                "This time we turn its white sticker to the front, so it dives through the front door.")],
         steps=[("U", "get ready", "Spin so the white faces **front**", "Turn it to face the front. ^U."),
                ("F'", "dive", "**Dive**", "It dives, ^F prime,"),
                ("U'", "prey walks", "The prey **walks over** it", "the prey walks over, ^U prime,"),
                ("F", "strike", "**Strike!**", "and it strikes. ^F."),
                ("U2", "swing away", "Swing the pair **away**", "Swing it away, ^U two,"),
                ("F' U F", "home", "**Open**, slide in, **close**", "and take it home. ^F prime, U, F.")],
         why=[(("•", "Same story, **mirrored**"),
               "It's the same story, just mirrored. If you've got the first crocodile, you've already got this one.")]),

    dict(chapter="Eagle", color=BLUE, animal=(EAGLE, "EAGLE"), title="The eagle swoops", alg="U R U2 R' U R U' R'",
         setup=["And here's the set-up for our last hunter."],
         spot=[((EAGLE, "White sticker points **up**: eagle"),
                "Last one. The white sticker is pointing straight up at the sky. That's an eagle."),
               (("•", "The prey must **drop** to the ground first"),
                "Eagles hunt from the air, so first, the prey has to come down to the ground.")],
         steps=[("U", "line up", "Line the prey up with its **side colour**",
                 "Look at the prey's side colour. It's red, so line it up over the red centre. ^U."),
                ("R", "drop", "Turn it **away** from its top colour",
                 "Its top colour is green, so we turn the red side away from green, ^R. And down it goes."),
                ("U2", "fly", "**Fly** over the prey", "Now the eagle flies over. ^U two."),
                ("R'", "grab", "**Grab!**", "And grabs it. ^R prime."),
                ("U", "swing away", "Swing the pair **away**", "Swing the pair away, ^U,"),
                ("R U' R'", "home", "**Open**, slide in, **close**", "and take it home. ^R, U prime, R prime.")],
         why=[(("•", "Turning toward green lifts a **solved** slot"),
               "Why away from green? Because turning the other way would lift a slot you've already solved.")],
         replay="Full speed. Line up, drop, fly over, grab, and home."),

    dict(chapter=None, color=PURPLE, animal=(None, "HUNTER"), title="Hunter stuck in the den", alg="F' U F R U R'",
         fix=True, setup=["Set this one up first."],
         spot=[(("•", "Hunter **stuck** in the den, twisted"),
                "Here, the hunter's stuck in its den, and it's twisted the wrong way.")],
         steps=[("F'", "lift", "**Lift** it out", "Lift it out with the front face. ^F prime."),
                ("U", "clear", "Step **clear**", "Step it clear, ^U,"),
                ("F", "put back", "Put the face **back**", "and put the face back. ^F.", "TIGER!"),
                ("R U R'", "pounce", "Tiger **pounce**",
                 "And look, it's a tiger, with its prey right behind it. You know this one. ^R, U, R prime.")]),
    dict(chapter=None, color=PURPLE, animal=(None, "HUNTER"), title="Prey stuck in the den", alg="F' U2 F R U R'",
         fix=True, setup=["Here's the set-up for the next one."],
         spot=[(("•", "Prey **stuck** in the den, flipped"),
                "This time, the prey is stuck in the den, flipped the wrong way. The hunter's waiting at the back.")],
         steps=[("F'", "lift", "**Lift** the prey out", "Lift the prey out. ^F prime."),
                ("U2", "clear", "Step **clear**", "Move it clear, ^U two,"),
                ("F", "put back", "Put the face **back**", "put the face back, ^F, and there's another tiger.",
                 "TIGER!"),
                ("R U R'", "pounce", "Tiger **pounce**", "So it pounces. ^R, U, R prime.")]),
    dict(chapter=None, color=PURPLE, animal=(None, "HUNTER"), title="Joined the wrong way", alg="F' U F U2 R U R'",
         fix=True, setup=["And the set-up for the last one."],
         spot=[(("•", "Touching, but joined **wrong**"),
                "In this one, they're touching, but they're joined the wrong way. So first, we split them up.")],
         steps=[("F'", "hide prey", "**Hide** the prey", "Hide the prey. ^F prime."),
                ("U", "walk away", "The hunter walks **away**", "Walk the hunter away, ^U,"),
                ("F", "bring back", "Bring the prey **back**", "and bring the prey back. ^F. Now they're apart."),
                ("U2", "to the den", "Tiger to its **den**", "Walk the tiger round to its den. ^U two.", "TIGER!"),
                ("R U R'", "pounce", "Tiger **pounce**", "And pounce. ^R, U, R prime.")],
         why=[(("•", "Every lift raised the **empty den**"),
               "Did you notice? Every time we lifted something, it was the empty den that came up. "
               "That's the golden rule, every time.")]),
]

SETUP_ITEMS = [("1", "Start **solved**: yellow top, green front"), ("2", "Do the **set-up moves** below"),
               ("3", "**Pause**, and try to solve it")]
HUNTER, PREY = (1, -1, 1), (1, 0, 1)
NARRATE = os.environ.get("NARRATION", "1") != "0"
BEAT = 0.5  # pause between the '|'-separated parts of one line


class Builder:
    def __init__(self, fps, dry=False):
        self.fps = fps
        self.dry = dry  # dry run: only collect the spoken lines, with estimated lengths
        self.lines = []  # every voiced part, in script order
        self.frames = []
        self.cube = Cube()
        self.pop = None  # (text, start_frame, frames, colour)
        self.cues = []  # (start seconds, wav path, text, duration)
        self.chapters = []  # (start seconds, title)
        self.speech_end = 0  # frame index where the current narration ends
        self.mark = None  # frame index of the '^' word in the current narration

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

    def chapter(self, title):
        self.chapters.append((len(self.frames) / self.fps, title))

    # -- narration
    def say(self, text):
        """Start speaking `text` now; returns its length in seconds and sets self.mark from any '^'."""
        t0 = t = len(self.frames) / self.fps
        self.mark = None
        for part in (p.strip() for p in text.split("|")):
            if not part:
                continue
            if self.dry or not NARRATE:
                self.lines.append(part)
                dur = read_time(part)
            else:
                from narrate import clip
                path, dur = clip(part)
                self.cues.append((t, path, part.replace("^", ""), dur))
            if "^" in part:
                from narrate import speakable
                frac = len(speakable(part.split("^")[0])) / max(1, len(speakable(part)))
                self.mark = int((t + frac * dur) * self.fps)
            t += dur + BEAT
        self.speech_end = int((t - BEAT) * self.fps)
        return t - BEAT - t0

    def wait_speech(self, base, pad=0.4):
        self.hold_frames(base, self.speech_end + int(pad * self.fps) - len(self.frames))

    def narrate(self, base, text, pad=0.5):
        self.say(text)
        self.wait_speech(base, pad)

    def reveal(self, base, head, color, lines, pad=0.5, before=None):
        """Card whose bullets appear one by one as each line is spoken. lines: [(bullet or None, text)]."""
        shown = []
        for k, (item, text) in enumerate(lines):
            if before:
                before(k)
            if item:
                shown.append(item)
            items = [(ic, tx, "new" if (item and j == len(shown) - 1) else "plain") for j, (ic, tx) in enumerate(shown)]
            self.narrate(dict(base, card=dict(head=head, color=color, items=items), den_tag=base.get("den_tag")
                              and self.den_empty()), text, pad)
        return [(ic, tx, "plain") for ic, tx in shown]

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

    def hold_frames(self, base, n):
        for _ in range(max(0, n)):
            self.emit(base)

    def hold(self, base, seconds):
        self.hold_frames(base, int(seconds * self.fps))

    def popup(self, text, color, seconds=1.4):
        self.pop = (text, len(self.frames), int(seconds * self.fps), color)

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
                self.popup("HOME!", (120, 255, 150), 1.6)
            elif self.paired() and not was_paired:
                self.popup("KILL!", (255, 205, 0), 1.3)
        self.hold(base, pause)


def read_time(text):
    return 0.36 * len(text.split()) + 0.3


def move_time(moves, seconds=0.6, pause=0.2):
    return sum(seconds * (1.35 if t.endswith("2") else 1) + pause for t in moves.split())


def set_up(B, case, base):
    """Build the case on a solved cube with the set-up moves, in their own clearly labelled bar."""
    toks = invert(case["alg"]).split()
    B.cube = Cube()
    sb = dict(base, tags=False, subtitle="These set-up moves **build** the case.  They are **not** the solution.",
              alg_tokens=toks, alg_chunks=[(0, len(toks), "set-up moves  ·  not the solution")], alg_cur=-1,
              alg_done=0, bar_style="setup")
    lines = case["setup"]
    moves_on = 1 if len(lines) > 1 else 0  # the line that the moves play under
    for k, text in enumerate(lines):
        n = k + 1 if len(lines) > 1 else len(SETUP_ITEMS)
        items = [(ic, tx, "new" if len(lines) > 1 and j == k else "plain") for j, (ic, tx) in enumerate(SETUP_ITEMS[:n])]
        fr = dict(sb, card=dict(head="TRY IT YOURSELF", color=SLATE, items=items))
        dur = B.say(text)
        if k == moves_on:
            B.hold(fr, min(1.2, dur * 0.3))
            for i, tok in enumerate(toks):
                B.move(dict(fr, alg_cur=i, alg_done=i), tok, seconds=0.42, pause=0.08, pops=False)
            sb["alg_done"] = len(toks)
            fr = dict(fr, alg_done=len(toks))
        B.wait_speech(fr, 0.6)
    B.hold(dict(fr, alg_done=len(toks)), 0.4)


def play_case(B, case, num, total):
    alg = case["alg"]
    B.pop = None
    tokens = alg.split()
    spans, start = [], 0
    for s in case["steps"]:
        spans.append((start, len(s[0].split()), s[1]))
        start += len(s[0].split())
    emo, name = case["animal"]
    chip = f"{name} · CASE {num} OF {total}" if not case.get("fix") else "STUCK PIECES"
    base = dict(kind="case", chip=chip, chip_color=case["color"], chip_emoji=emo, title=case["title"],
                subtitle=f"Solved in **{len(tokens)} moves**", tags=True, animal=(emo, name), alg_tokens=tokens,
                alg_chunks=spans, alg_cur=-1, alg_done=0)

    # try it yourself: the set-up moves
    set_up(B, case, base)
    B.cube = Cube().run(invert(alg))

    # spot it
    B.reveal(dict(base, den_tag=True), "SPOT IT", case["color"], case["spot"])

    # solve it
    steps = case["steps"]
    done = 0
    for k, step in enumerate(steps):
        m, _, bullet, spoken = step[:4]
        items = [(str(j + 1), s[2], "done" if j < k else ("active" if j == k else "todo")) for j, s in enumerate(steps)]
        fr = dict(base, card=dict(head="SOLVE IT", color=case["color"], items=items), chunk_hint=k, alg_done=done)
        dur = B.say(spoken)
        if B.mark is not None:
            B.hold_frames(fr, max(int(0.35 * B.fps), B.mark - len(B.frames) - int(0.1 * B.fps)))
        else:
            B.hold(fr, min(max(0.5, dur * 0.5), max(0.5, dur - move_time(m))))
        for tok in m.split():
            B.move(dict(fr, alg_cur=done, alg_done=done), tok)
            done += 1
        if len(step) > 4:
            B.popup(step[4], (255, 150, 60), 1.5)
        B.wait_speech(dict(fr, alg_done=done), 0.5)
    finished = [(str(j + 1), s[2], "done") for j, s in enumerate(steps)]
    end = dict(base, alg_done=done, card=dict(head="SOLVE IT", color=case["color"], items=finished))

    # why it works
    if case.get("why"):
        B.reveal(dict(end, chip="WHY IT WORKS"), "WHY IT WORKS", case["color"], case["why"], pad=0.7)

    # replay at solving speed
    if case.get("replay"):
        B.cube = Cube().run(invert(alg))
        rb = dict(end, speed_label="FULL SPEED", alg_done=0)
        B.say(case["replay"])
        B.hold(rb, 0.9)
        for i, tok in enumerate(tokens):
            B.move(dict(rb, alg_cur=i, alg_done=i), tok, seconds=0.32, pause=0.06, pops=False)
        B.wait_speech(dict(rb, alg_done=len(tokens)), 0.3)
        if case.get("after"):
            B.narrate(dict(rb, alg_done=len(tokens)), case["after"], 0.5)
        B.hold(dict(rb, alg_done=len(tokens)), 0.7)


def build_timeline(fps=30):
    """The whole video. With narration on, every line is voiced first, in order, so each one hears its neighbours."""
    if NARRATE:
        from narrate import prepare
        prepare(_build(fps, dry=True).lines)
    return _build(fps)


def _build(fps, dry=False):
    B = Builder(fps, dry)
    TIGER_SETUP = invert("R U R'")

    # ---- hook: a 3-move solve before anything else
    B.chapter("Intro")
    B.cube = Cube().run(TIGER_SETUP)
    hook = dict(kind="hook", cube_xy=(640, 300), cube_scale=100, tags=True, animal=(TIGER, "TIGER"), glow=True)
    B.narrate(hook, "See these two pieces? Watch.", 0.3)
    for tok in "R U R'".split():
        B.move(hook, tok, seconds=0.5, pause=0.15)
    done = dict(hook, headline="3 moves.")
    B.narrate(done, "Three moves, and that pair's home.", 0.5)
    B.narrate(dict(done, headline="No memorising.  Just 3 animals.", emojis=(CROC, TIGER, EAGLE)),
              "By the end of this video, you'll be able to do that with any pair. No memorising, just three animals.",
              0.7)

    # ---- title card
    B.cube = Cube()
    B.say("This is the F2L Hunting Story. So grab your cube, and let's get into it.")
    n = max(int(4 * fps), B.speech_end - len(B.frames) + int(0.8 * fps))
    for k in range(n):
        B.emit(dict(kind="title", yaw=-38 + 25 * math.sin(2 * math.pi * k / (6 * fps)),
                    cube_xy=(900, 370), cube_scale=125, glow=False))

    # ---- what is F2L + the cast
    B.chapter("What is F2L?")
    B.cube = Cube().run(TIGER_SETUP)
    base = dict(kind="intro", chip="WHAT IS F2L?", chip_color=PURPLE, title="First two layers", glow=False)
    B.reveal(base, "IN 4 STEPS", PURPLE, [
        (("1", "White cross on the **bottom**"),
         "A quick refresher first. F2L means the first two layers, and you've already got your white cross on the "
         "bottom."),
        (("2", "Pair a **corner** with its **edge**"), "Now we pair up a corner with its matching edge,"),
        (("3", "Drop the pair into its **slot**"), "and drop that pair into its slot."),
        (("4", "Four slots: **first two layers** done"), "Do that four times, and the first two layers are done.")])
    base = dict(kind="intro", chip="MEET THE CAST", chip_color=PURPLE, title="Who's who?", tags=True,
                animal=(None, "HUNTER"), den_tag=True)
    B.reveal(base, "THE STORY", PURPLE, [
        (("•", "**Hunter**: the white corner"),
         "To make this stick, we'll tell it as a story. The white corner is our hunter."),
        (("•", "**Prey**: the edge with the same colours"), "The edge with the same two colours is its prey."),
        (("•", "**Den**: the empty slot"), "And this empty slot down here is its den. That's home."),
        (("•", "Hunter catches prey: **KILL!** Then home"),
         "When the hunter catches the prey, they join up. That's the kill. Then it carries its prey home.")])

    # ---- the three rules, shown on the cube
    B.chapter("The rules")
    B.cube = Cube().run(TIGER_SETUP)
    rb = dict(kind="intro", chip="THE RULES", chip_color=PURPLE, title="Three rules", glow=False)
    rules = [
        (("1", "Top layer turns **freely**"),
         "There are just three rules. First, the top layer is free. Turn it as much as you like.",
         [("U", None), ("U'", None)]),
        (("2", "Side face: a quarter turn **out**, then straight **back**"),
         "Second, a side face only turns a quarter turn out, and then it comes straight back.",
         [("R", None), ("R'", None)]),
        (("3", "Golden rule: only lift the **empty den**"),
         "And third, the golden rule. When a side face turns, one of the slots comes up to the top. "
         "Make sure it's the empty den, and never a slot you've already solved.",
         [("R'", ("SOLVED SLOT!", (255, 90, 90))), ("R", None), ("R", ("EMPTY DEN!", (120, 255, 150))), ("R'", None)]),
    ]
    shown = []
    for item, text, demo in rules:
        shown.append(item)
        items = [(ic, tx, "new" if j == len(shown) - 1 else "plain") for j, (ic, tx) in enumerate(shown)]
        fr = dict(rb, card=dict(head="THE RULES", color=PURPLE, items=items))
        dur = B.say(text)
        B.hold(fr, max(0.6, dur - sum(1.4 for _ in demo)))
        for tok, pop in demo:
            B.move(dict(fr, speed_label=f"move: {tok}"), tok, seconds=0.7, pause=0.1, pops=False)
            if pop:
                B.popup(pop[0], pop[1], 1.4)
                B.hold(dict(fr, speed_label=f"move: {tok}"), 1.0)
        B.wait_speech(fr, 0.6)

    # ---- spot the hunter: the example on the cube changes with each bullet
    B.chapter("Spot the hunter")
    examples = [(TIGER_SETUP, (TIGER, "TIGER")), (invert(CASES[2]["alg"]), (CROC, "CROCODILE")),
                (invert(CASES[4]["alg"]), (EAGLE, "EAGLE"))]
    sb = dict(kind="intro", chip="SPOT THE HUNTER", chip_color=PURPLE, title="Which hunter is it?", tags=True)
    cur = {}

    def show_example(k):
        if k < len(examples):
            B.cube = Cube().run(examples[k][0])
            cur["animal"] = examples[k][1]

    shown = []
    for k, (item, text) in enumerate([
            ((TIGER, "Top colours **different**: tiger"),
             "So, which hunter have you got? Look at the top colours of the two pieces. "
             "If they're different, like a tiger's stripes, it's a tiger."),
            ((CROC, "Top colours **the same**: crocodile"), "If they're the same colour, it's a crocodile."),
            ((EAGLE, "White sticker **up**: eagle"),
             "And if the white sticker is pointing up at the sky, it's an eagle. That's all three.")]):
        show_example(k)
        shown.append(item)
        items = [(ic, tx, "new" if j == len(shown) - 1 else "plain") for j, (ic, tx) in enumerate(shown)]
        B.narrate(dict(sb, animal=cur["animal"], card=dict(head="LOOK AT THE TOP", color=PURPLE, items=items)), text,
                  0.6)

    # ---- the five basic cases, then the stuck pieces
    basics = [c for c in CASES if not c.get("fix")]
    for i, case in enumerate(basics, 1):
        if case["chapter"]:
            B.chapter(case["chapter"])
        play_case(B, case, i, len(basics))

    B.chapter("Stuck pieces")
    fixes = [c for c in CASES if c.get("fix")]
    B.cube = Cube().run(invert(fixes[0]["alg"]))
    base = dict(kind="intro", chip="STUCK PIECES", chip_color=PURPLE, title="When a piece is stuck", tags=True,
                animal=(None, "HUNTER"))
    B.reveal(base, "THE PLAN", PURPLE, [
        (None, "Now, sometimes a piece gets stuck in the den, or the two pieces are stuck together. "
               "Don't worry, there's an easy way out."),
        (("1", "**Lift** it out"), "Lift it out,"),
        (("2", "Step it **clear**"), "step it clear,"),
        (("3", "Put the face **back**"), "and put the face back."),
        ((TIGER, "Make it come up as a **tiger**"),
         "And here's the trick. Lift it so it comes up as a tiger, with the prey right behind it. "
         "Then you already know how to finish.")])
    for case in fixes:
        play_case(B, case, 0, 0)

    # ---- recap and goodbye
    B.chapter("Recap")
    table = [
        (TIGER, "Tiger", "different top colours", "R U R'", "Jump, drag back, home."),
        (CROC, "Crocodile", "same top colours", "U' R U R'  +  U2 R U' R'", "Hide, prey walks over, strike. Then home."),
        (EAGLE, "Eagle", "white sticker up", "U R U2 R'  +  U R U' R'", "Line up, drop, fly over, grab. Then home."),
        (None, "Stuck?", "in the den, or joined wrong", "lift · clear · put back", "Bring it up as a tiger, then pounce."),
    ]
    B.cube = Cube()
    base = dict(kind="outro", show_cube=False, chip="RECAP", chip_color=PURPLE,
                title="Three hunters, one golden rule", table=table,
                footer="Golden rule: only lift the empty den.      Mirror: R → F',  U → U'")
    for text in ["Let's recap. Different colours on top? That's a tiger. Jump, drag back, and home.",
                 "The same colours? Crocodile. Hide, let the prey walk over, then strike.",
                 "White sticker up? Eagle. Line up, drop, fly over, and grab.",
                 "And if anything's stuck, lift it out so it comes up as a tiger. "
                 "Just remember the golden rule. Only ever lift the empty den."]:
        B.narrate(base, text, 0.6)
    B.cube = Cube()
    base = dict(kind="intro", chip="KEEP HUNTING", chip_color=PURPLE, title="Happy hunting!", glow=False,
                credits=True)
    B.reveal(base, "YOUR NEXT STEPS", PURPLE, [
        (("1", "Go **slow**. Say the story out loud"),
         "Don't worry if it feels slow at first. Everyone's F2L is slow at first."),
        (("2", "The speed comes **on its own**"), "Say the story out loud as you turn, and the speed will come on its own."),
        (("3", "Which hunter was **hardest**? Comment below"),
         "Which hunter gave you the most trouble? Let me know in the comments. Happy hunting.")])
    B.hold(dict(base, card=None), 2.0)
    return B
