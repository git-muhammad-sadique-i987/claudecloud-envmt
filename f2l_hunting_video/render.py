"""Render the F2L Hunting Story video (3D animated cube + bullet cards + voiceover) to MP4.

Usage:  python render.py [out.mp4] [--preview N]   (--preview renders only every Nth frame)
        python render.py --thumbnail thumb.png
Also writes <out>.srt (closed captions) and youtube_description.txt (with chapter timestamps).
Narration: see narrate.py (Kokoro, Piper or Windows SAPI); NARRATION=0 for none.
"""
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from cube import Cube, MOVES, invert, parse, rot
from story import build_timeline

W, H = 1280, 720
SS = 2  # supersampling factor
FPS = 30

INTER_DIR = "/usr/share/fonts/opentype/inter/"
WIN_FONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
SEGOE = {"Black": "seguibl.ttf", "Bold": "segoeuib.ttf", "SemiBold": "seguisb.ttf",
         "Medium": "seguisb.ttf", "Regular": "segoeui.ttf"}
EMOJI_FONT = os.path.join(WIN_FONTS, "seguiemj.ttf")
_fonts = {}


def font_path(weight):
    inter = f"{INTER_DIR}Inter-{weight}.otf"
    if os.path.exists(inter):
        return inter
    return os.path.join(WIN_FONTS, SEGOE[weight])


def font(size, weight="Bold"):
    key = (size, weight)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(font_path(weight), size * SS)
    return _fonts[key]


def emoji(draw, x, y, ch, size):
    """Colour emoji (Segoe UI Emoji); skipped where the font is missing. Returns its width."""
    if not ch or not os.path.exists(EMOJI_FONT):
        return 0
    key = (size, "emoji")
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(EMOJI_FONT, size * SS)
    draw.text(S(x, y), ch, font=_fonts[key], embedded_color=True)
    return _fonts[key].getlength(ch) / SS


RGB = {
    "W": (245, 245, 245), "Y": (255, 213, 0), "G": (0, 170, 80),
    "B": (20, 90, 220), "R": (215, 30, 40), "O": (255, 120, 0),
}
ANIMALS = ("\U0001F40A", "\U0001F405", "\U0001F985")
CREDIT = ("Story: RiDo's \"Hunting Story for F2L\".  Teaching flow: ParadoxCubing's \"F2L For Beginners\".")
GREY = (74, 74, 84)
BODY = (14, 14, 18)
HUNTER, PREY = (1, -1, 1), (1, 0, 1)

# ---------------------------------------------------------------- background


def make_background():
    y, x = np.mgrid[0:H * SS, 0:W * SS].astype(np.float32)
    x /= W * SS
    y /= H * SS
    d = np.sqrt((x - 0.72) ** 2 * 1.6 + (y - 0.45) ** 2)
    t = np.clip(1 - d / 0.85, 0, 1) ** 1.6
    base = np.array([16, 12, 28], np.float32)
    glow = np.array([70, 28, 64], np.float32)
    img = base + (glow - base) * t[..., None]
    return Image.fromarray(img.astype(np.uint8))


BG = None

# ---------------------------------------------------------------- 3D cube


def view_matrix(yaw_deg):
    return rot(0, math.radians(28)) @ rot(1, math.radians(yaw_deg))


def sticker_color(home, col, is_center):
    home = tuple(int(v) for v in home)
    if home in (HUNTER, PREY) or is_center:
        return RGB[col]
    if home[1] == 1:  # last-layer pieces: not part of the story
        return GREY
    c = RGB[col]  # already-solved F2L pieces: dimmed
    return tuple(int(v * 0.45 + 30) for v in c)


def rounded_square(h, r, n=5):
    pts = []
    for cx, cy, a0 in ((h - r, h - r, 0), (-h + r, h - r, 90), (-h + r, -h + r, 180), (h - r, -h + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


RSQ = rounded_square(0.42, 0.09)
CAM_F = 9.0


def project(p, cx, cy, scale):
    k = CAM_F / (CAM_F - p[2])
    return (cx + p[0] * scale * k, cy - p[1] * scale * k)


def cubie_mats(cube, frame):
    """Current full matrix of each cubie, including a partially animated layer turn."""
    mats = [M.copy() for M in frame["state"]]
    anim = frame.get("anim")
    if anim:
        idxs, axis, angle = anim
        R = rot(axis, angle)
        for i in idxs:
            mats[i] = R @ mats[i]
    return mats


def sticker_anchor(c, M, V, prefer=None):
    """View-space centre of the cubie's sticker that faces the camera most.

    prefer="W" favours the white sticker and prefer="up" the sticker facing up, whenever it is visible.
    Labels point here rather than at the cubie's centre, which sits inside the cube and so lands on a
    neighbouring sticker on screen.
    """
    cam = np.array([0, 0, CAM_F])
    center = V @ (M @ c.home)
    best = None
    for n, col in c.stickers:
        nv = V @ (M @ n)
        fc = center + 0.5 * nv
        facing = float(np.dot(nv, (cam - fc) / np.linalg.norm(cam - fc)))
        wanted = col == prefer or (prefer == "up" and (M @ n)[1] > 0.9)
        score = facing + (1.0 if wanted and facing > 0.2 else 0.0)
        if best is None or score > best[0]:
            best = (score, fc)
    return best[1]


def draw_cube(draw, cube, mats, V, cx, cy, scale, glow):
    faces = []
    cam = np.array([0, 0, CAM_F])
    for c, M in zip(cube.cubies, mats):
        center = V @ (M @ c.home)
        axes = V @ M  # columns: rotated local axes in view space
        sticker_by_normal = {tuple(n.astype(int)): col for n, col in c.stickers}
        is_center = c.kind() == 1
        is_target = tuple(int(v) for v in c.home) in (HUNTER, PREY)
        for i in range(3):
            for s in (1, -1):
                n = axes[:, i] * s
                fc = center + 0.5 * n
                if np.dot(n, cam - fc) <= 0:
                    continue
                u, v = axes[:, (i + 1) % 3], axes[:, (i + 2) % 3]
                body = [fc + a * 0.5 * u + b * 0.5 * v for a, b in ((1, 1), (-1, 1), (-1, -1), (1, -1))]
                ln = [0, 0, 0]
                ln[i] = s
                col = sticker_by_normal.get(tuple(ln))
                stk = None
                if col:
                    base = sticker_color(c.home, col, is_center)
                    light = 0.62 + 0.38 * max(0.0, float(np.dot(n, np.array([0.3, 0.8, 0.5]))))
                    fill = tuple(min(255, int(ch * light)) for ch in base)
                    sp = fc + 0.002 * n
                    stk = ([sp + a * u + b * v for a, b in RSQ], fill, is_target and glow)
                faces.append((float(np.mean([p[2] for p in body])), body, stk))
    faces.sort(key=lambda f: f[0])
    for _, body, stk in faces:
        draw.polygon([project(p, cx, cy, scale) for p in body], fill=BODY)
        if stk:
            pts = [project(p, cx, cy, scale) for p in stk[0]]
            draw.polygon(pts, fill=stk[1])
            if stk[2]:
                draw.line(pts + [pts[0]], fill=(255, 255, 255), width=int(2.5 * SS))


# ---------------------------------------------------------------- 2D overlay helpers


def S(*v):
    return tuple(int(x * SS) for x in v)


def text_w(txt, f):
    return f.getlength(txt) / SS


def pill(draw, x, y, txt, f, fill, color=(255, 255, 255), pad=(14, 6), anchor_center=False):
    w = text_w(txt, f) + pad[0] * 2
    h = f.size / SS + pad[1] * 2 + 2
    if anchor_center:
        x -= w / 2
    draw.rounded_rectangle(S(x, y, x + w, y + h), radius=int(h * SS / 2), fill=fill)
    draw.text(S(x + pad[0], y + pad[1] - 1), txt, font=f, fill=color)
    return w, h


def chip(draw, x, y, txt, fill, emo=None):
    """Section pill, with an optional emoji in front."""
    f = font(18)
    ew = 30 if emo and os.path.exists(EMOJI_FONT) else 0
    w, h = text_w(txt, f) + 28 + ew, f.size / SS + 14
    draw.rounded_rectangle(S(x, y, x + w, y + h), radius=int(h * SS / 2), fill=fill)
    if ew:
        emoji(draw, x + 10, y + 1, emo, 22)
    draw.text(S(x + 14 + ew, y + 6), txt, font=f, fill=(255, 255, 255))


def rich_wrap(text, f, fb, width):
    """Wrap 'plain **highlighted** plain' into lines of (word, highlighted) pairs."""
    words = []  # (word, highlighted, glued to the previous word)
    parts = text.split("**")
    for k, part in enumerate(parts):
        touching = k > 0 and parts[k - 1][-1:] not in ("", " ") and part[:1] not in ("", " ")
        for j, w in enumerate(part.split()):
            words.append((w, k % 2 == 1, j == 0 and touching))
    lines, cur, w = [], [], 0
    space = text_w(" ", f)
    for word, em, glue in words:
        ww = text_w(word, fb if em else f)
        gap = 0 if glue or not cur else space
        if cur and not glue and w + gap + ww > width:
            lines.append(cur)
            cur, w, gap = [], 0, 0
        w += gap + ww
        cur.append((word, em, glue))
    if cur:
        lines.append(cur)
    return lines


def draw_rich(draw, x, y, line, f, fb, col, ecol):
    space = text_w(" ", f)
    for k, (word, em, glue) in enumerate(line):
        if k and not glue:
            x += space
        draw.text(S(x, y), word, font=fb if em else f, fill=ecol if em else col)
        x += text_w(word, fb if em else f)


CARD_X0, CARD_X1 = 40, 566


def card(draw, c, y0=178):
    """Bullet card: a coloured header, then items (icon, text, state).
    state: plain | new (just added) | todo | active | done."""
    f, fb = font(24, "SemiBold"), font(24, "Bold")
    rows = [rich_wrap(tx, f, fb, CARD_X1 - CARD_X0 - 96) for _, tx, _ in c["items"]]
    h = 60 + sum(len(r) * 33 + 18 for r in rows)
    draw.rounded_rectangle(S(CARD_X0, y0, CARD_X1, y0 + h), radius=18 * SS, fill=(28, 22, 46),
                           outline=(80, 68, 120), width=2 * SS)
    pill(draw, CARD_X0 + 20, y0 + 16, c["head"], font(16), c["color"], pad=(12, 5))
    y = y0 + 62
    for (icon, _, st), lines in zip(c["items"], rows):
        rh = len(lines) * 33
        if st in ("active", "new"):
            draw.rounded_rectangle(S(CARD_X0 + 10, y - 8, CARD_X1 - 10, y + rh + 2), radius=12 * SS,
                                   fill=(60, 48, 96))
        cx, cy = CARD_X0 + 40, y + 16
        if st == "done":
            draw.ellipse(S(cx - 13, cy - 13, cx + 13, cy + 13), fill=(40, 150, 90))
            draw.line(S(cx - 6, cy, cx - 1, cy + 6, cx + 7, cy - 6), fill=(255, 255, 255), width=3 * SS)
        elif icon and icon.isdigit():
            fill = {"active": (255, 205, 0), "todo": None}.get(st, c["color"])
            draw.ellipse(S(cx - 14, cy - 14, cx + 14, cy + 14), fill=fill, outline=(140, 130, 180) if not fill else None,
                         width=2 * SS)
            fn = font(17)
            draw.text(S(cx - text_w(icon, fn) / 2, cy - 12), icon, font=fn,
                      fill=(20, 16, 30) if st == "active" else (255, 255, 255))
        elif icon == "•":
            draw.ellipse(S(cx - 6, cy - 6, cx + 6, cy + 6), fill=c["color"])
        elif icon:
            emoji(draw, cx - 17, cy - 19, icon, 30)
        col, ecol = {"todo": ((130, 122, 160), (170, 150, 95)),
                     "done": ((185, 220, 195), (140, 215, 165))}.get(st, ((255, 255, 255), (255, 205, 0)))
        for k, ln in enumerate(lines):
            draw_rich(draw, CARD_X0 + 72, y + k * 33, ln, f, fb, col, ecol)
        y += rh + 18


def tag(draw, anchor, txt, fill, color, side, emo=None, xmin=12):
    """Label with a leader line pointing at a piece (and an optional emoji badge)."""
    ax, ay = anchor
    f = font(17)
    ew = 34 if emo and os.path.exists(EMOJI_FONT) else 0
    w = text_w(txt, f) + 24 + ew
    h = 30
    tx = min(max(ax + (70 if side > 0 else -70 - w), xmin), W - 12 - w)  # stay on screen, clear of the card
    ty = max(ay - 75, 8)
    lx = min((tx, tx + w), key=lambda x: abs(x - ax))
    draw.line(S(ax, ay, lx, ty + h / 2), fill=fill, width=3 * SS)
    draw.ellipse(S(ax - 6, ay - 6, ax + 6, ay + 6), fill=fill, outline=(0, 0, 0), width=2 * SS)
    if ew:
        draw.rounded_rectangle(S(tx, ty, tx + w, ty + h), radius=int(h * SS / 2), fill=fill)
        emoji(draw, tx + 7, ty + 1, emo, 26)
        draw.text(S(tx + 12 + ew, ty + 4), txt, font=f, fill=color)
    else:
        pill(draw, tx, ty, txt, f, fill, color, pad=(12, 5))


def alg_bar(draw, fr, y):
    toks, chunks = fr["alg_tokens"], fr.get("alg_chunks")
    cur, done = fr.get("alg_cur", -1), fr.get("alg_done", 0)
    setup = fr.get("bar_style") == "setup"  # set-up moves: blue, so they never look like the solve
    f = font(26)
    bw, gap, cgap = 62, 8, 26
    chunk_of = []
    for ci, (start, n, _) in enumerate(chunks):
        chunk_of += [ci] * n
    total = len(toks) * bw + (len(toks) - 1) * gap + (len(chunks) - 1) * (cgap - gap)
    x = (W - total) / 2
    pos = []
    for i, t in enumerate(toks):
        if i and chunk_of[i] != chunk_of[i - 1]:
            x += cgap - gap
        pos.append(x)
        if i == cur:
            fill, tc, ol = ((150, 185, 255), (20, 16, 30), (205, 220, 255)) if setup else                 ((255, 205, 0), (20, 16, 30), (255, 230, 120))
        elif i < done:
            fill, tc, ol = ((58, 72, 118), (205, 215, 255), None) if setup else ((40, 120, 70), (220, 255, 230), None)
        else:
            fill, tc, ol = (34, 30, 52), (255, 255, 255), (110, 100, 150)
        y0 = y - (6 if i == cur else 0)
        draw.rounded_rectangle(S(x, y0, x + bw, y0 + 54), radius=12 * SS, fill=fill,
                               outline=ol, width=2 * SS if ol else 0)
        tw = text_w(t, f)
        draw.text(S(x + (bw - tw) / 2, y0 + 11), t, font=f, fill=tc)
        x += bw + gap
    fl = font(15, "SemiBold")
    active_chunk = chunk_of[cur] if 0 <= cur < len(toks) else fr.get("chunk_hint", -1)
    for ci, (start, n, label) in enumerate(chunks):
        x0, x1 = pos[start], pos[start + n - 1] + bw
        col = (150, 185, 255) if setup else (255, 205, 0) if ci == active_chunk else (150, 140, 190)
        draw.line(S(x0 + 4, y + 64, x1 - 4, y + 64), fill=col, width=3 * SS)
        lw = text_w(label, fl)
        draw.text(S((x0 + x1) / 2 - lw / 2, y + 72), label, font=fl, fill=col)


def pop_text(draw, txt, t, color, cx=880):
    """Big centred word that pops in (t in 0..1 over its lifetime)."""
    sc = min(1.0, t * 5) if t < 0.2 else 1.0
    size = int(64 * (0.6 + 0.4 * sc))
    f = font(size, "Black")
    w = text_w(txt, f)
    x, y = cx - w / 2, 70
    for dx, dy in ((3, 3), (-2, 2)):
        draw.text(S(x + dx, y + dy), txt, font=f, fill=(0, 0, 0))
    draw.text(S(x, y), txt, font=f, fill=color)


# ---------------------------------------------------------------- frame


def render(fr):
    img = BG.copy()
    draw = ImageDraw.Draw(img)
    cube = CUBE
    kind = fr["kind"]

    if fr.get("show_cube", True):
        V = view_matrix(fr.get("yaw", -38))
        cx, cy, scale = fr.get("cube_xy", (890, 318)) + (fr.get("cube_scale", 104),)
        mats = cubie_mats(cube, fr)
        draw_cube(draw, cube, mats, V, cx * SS, cy * SS, scale * SS, fr.get("glow", True))
        if fr.get("tags"):
            idx = {tuple(int(v) for v in c.home): i for i, c in enumerate(cube.cubies)}
            emo, name = fr.get("animal", (None, "HUNTER"))
            anchors = [project(sticker_anchor(cube.cubies[idx[h]], mats[idx[h]], V, pref), cx, cy, scale)
                       for h, pref in ((HUNTER, "W"), (PREY, "up"))]
            side = 1 if anchors[0][0] >= anchors[1][0] - 5 else -1  # labels fan out, away from each other
            for a, txt, fill, s, e in ((anchors[0], name, (255, 255, 255), side, emo),
                                       (anchors[1], "PREY", (255, 140, 30), -side, None)):
                tag(draw, a, txt, fill, (20, 16, 30), s, e, CARD_X1 + 10 if fr.get("card") else 12)
        if fr.get("den_tag"):
            p = V @ np.array([1.5, -0.5, 1.5])  # the outside edge of the front-right slot
            tag(draw, project(p, cx, cy, scale), "DEN (empty slot)", (120, 200, 255), (10, 20, 40), 1)

    if kind == "title":
        draw.text(S(70, 120), "F2L", font=font(120), fill=(255, 205, 0))
        draw.text(S(70, 275), "THE HUNTING", font=font(64), fill=(255, 255, 255))
        draw.text(S(70, 350), "STORY", font=font(64), fill=(255, 255, 255))
        x = 290
        for e in ANIMALS:
            x += emoji(draw, x, 352, e, 52) + 10
        x = 70
        for txt, col in (("5 CASES", (40, 150, 90)), ("3 ANIMALS", (240, 110, 30)),
                         ("NO ALGORITHMS", (70, 140, 240))):
            x += pill(draw, x, 460, txt, font(22), col)[0] + 12
        draw.text(S(70, 540), "Based on RiDo's “Hunting Story for F2L”", font=font(22, "SemiBold"),
                  fill=(225, 220, 240))
        draw.text(S(70, 577), "Teaching flow inspired by ParadoxCubing's “F2L For Beginners”",
                  font=font(16, "Regular"), fill=(150, 145, 170))

    if kind == "hook" and fr.get("headline"):
        f = font(52, "Black")
        txt = fr["headline"]
        ew = 3 * 62 if fr.get("emojis") else 0
        x = (W - text_w(txt, f) - ew) / 2
        for dx, dy in ((3, 3), (-2, 2)):
            draw.text(S(x + dx, 590 + dy), txt, font=f, fill=(0, 0, 0))
        draw.text(S(x, 590), txt, font=f, fill=(255, 255, 255))
        x += text_w(txt, f) + 14
        for e in fr.get("emojis") or ():
            x += emoji(draw, x, 588, e, 52) + 8

    if kind in ("intro", "case", "outro"):
        if fr.get("chip"):
            chip(draw, 50, 34, fr["chip"], fr.get("chip_color", (150, 60, 200)), fr.get("chip_emoji"))
        if fr.get("title"):
            draw.text(S(50, 80), fr["title"], font=font(40), fill=(255, 255, 255))
        if fr.get("subtitle"):
            f, fb = font(19, "Medium"), font(19, "Bold")
            for ln in rich_wrap(fr["subtitle"], f, fb, 1180)[:1]:
                draw_rich(draw, 52, 134, ln, f, fb, (190, 180, 220), (255, 205, 0))

    if fr.get("card") and fr["card"]["items"]:
        card(draw, fr["card"])

    if fr.get("credits"):
        draw.text(S(50, 640), CREDIT, font=font(16, "Regular"), fill=(170, 165, 195))

    if fr.get("table"):
        y = 150
        for emo, name, recog, alg, note in fr["table"]:
            draw.rounded_rectangle(S(60, y, 1220, y + 86), radius=14 * SS, fill=(30, 24, 48))
            x0 = 84 + (emoji(draw, 80, y + 18, emo, 40) + 8 if emo else 0)
            draw.text(S(x0, y + 10), name, font=font(26), fill=(255, 205, 0))
            draw.text(S(x0, y + 46), recog, font=font(17, "SemiBold"), fill=(120, 200, 255))
            draw.text(S(470, y + 10), alg, font=font(26), fill=(255, 255, 255))
            draw.text(S(470, y + 50), note, font=font(17, "Medium"), fill=(190, 180, 220))
            y += 98

    if fr.get("footer"):
        draw.text(S(60, 562), fr["footer"], font=font(22, "SemiBold"), fill=(120, 200, 255))

    if fr.get("alg_tokens"):
        alg_bar(draw, fr, 600)

    if fr.get("pop"):
        txt, t, color = fr["pop"]
        pop_text(draw, txt, t, color, fr.get("cube_xy", (880, 0))[0])

    if fr.get("speed_label"):
        pill(draw, 1100, 34, fr["speed_label"], font(16), (60, 50, 90))

    return img.resize((W, H), Image.LANCZOS).tobytes()


CUBE = None


def init_worker():
    global BG, CUBE
    BG = make_background()
    CUBE = Cube()


def thumbnail(out):
    """1280x720 YouTube thumbnail: the tiger case on a big cube, the title, and the credit to RiDo."""
    init_worker()
    fr = dict(kind="thumb", state=Cube().run("R U' R'").snapshot(), anim=None, cube_xy=(915, 395),
              cube_scale=145, tags=True, animal=(ANIMALS[1], "TIGER"), glow=True)
    img = Image.frombytes("RGB", (W, H), render(fr))
    draw = ImageDraw.Draw(img)
    black = lambda size: ImageFont.truetype(font_path("Black"), size)
    draw.text((56, 22), "F2L", font=black(170), fill=(255, 205, 0), stroke_width=6, stroke_fill=(0, 0, 0))
    for k, line in enumerate(("HUNTING", "STORY")):
        draw.text((60, 222 + k * 84), line, font=black(80), fill=(255, 255, 255), stroke_width=4,
                  stroke_fill=(0, 0, 0))
    if os.path.exists(EMOJI_FONT):
        ef = ImageFont.truetype(EMOJI_FONT, 72)
        for k, e in enumerate(ANIMALS):
            draw.text((62 + k * 104, 420), e, font=ef, embedded_color=True)
    small = black(32)
    txt = "NO ALGORITHMS"
    w = small.getlength(txt) + 40
    draw.rounded_rectangle((62, 540, 62 + w, 594), radius=27, fill=(215, 30, 40))
    draw.text((82, 546), txt, font=small, fill=(255, 255, 255))
    draw.text((64, 618), "Based on RiDo's Hunting Story", font=ImageFont.truetype(font_path("Bold"), 30),
              fill=(235, 230, 245), stroke_width=3, stroke_fill=(0, 0, 0))
    img.save(out)
    print("wrote", out)


def youtube_description(chapters, out):
    from story import CASES
    stamps = "\n".join(f"{int(t // 60)}:{int(t % 60):02d} {name}" for t, name in chapters)
    setups = "\n".join(f"{c['title']}: {invert(c['alg'])}" for c in CASES)
    text = f"""Title:
F2L Hunting Story: Solve Every Pair with 3 Animals 🐊🐅🦅 | Beginner CFOP (No Algorithms)

Description:
This video retells RiDo's brilliant "Hunting Story for F2L", so please go and watch the originals too:
Part 1: https://www.youtube.com/watch?v=WB5apB2i_Do
Part 2: https://www.youtube.com/watch?v=Q2uWq2q3Xoc

Solve the first two layers of the Rubik's Cube without memorising 41 algorithms. Every F2L pair is a hunter (the white corner) catching its prey (the matching edge) and carrying it home to its den (the empty slot).

🐅 Tiger: different colours on top. Jump, drag back, home (R U R').
🐊 Crocodile: the same colour on top. Hide, let the prey walk over, strike, then home.
🦅 Eagle: the white sticker points up. Line up, drop, fly over, grab, then home.
Plus how to get stuck pieces out, and the golden rule that keeps your solved slots safe.

Try it yourself: every case starts with set-up moves. Hold a solved cube with yellow on top and green in front, do the set-up moves to build the case, then pause and try to solve it. The set-up moves are not the solution.
{setups}

Chapters
{stamps}

Credits
The hunting story (hunters, prey, den, kill zone and the golden rule) comes from RiDo's "Hunting Story for F2L" (links above).
The teaching flow follows ParadoxCubing's "F2L For Beginners | Easy CFOP Tutorial":
https://www.youtube.com/watch?v=Hx9ZbPdX8zM

#rubikscube #f2l #cfop #cubing #huntingstory
"""
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    out = "f2l_hunting_story.mp4"
    step = 1
    args = sys.argv[1:]
    if "--thumbnail" in args:
        thumbnail(args[args.index("--thumbnail") + 1])
        return
    if "--preview" in args:
        step = int(args[args.index("--preview") + 1])
        args = [a for a in args if a not in ("--preview", str(step))]
    if args:
        out = args[0]
    timeline = build_timeline(FPS)
    frames = timeline.frames[::step]
    total = len(timeline.frames) / FPS
    print(f"{len(frames)} frames, {total:.1f}s, {len(timeline.cues)} narration clips", flush=True)
    silent = out + ".video.mp4" if timeline.cues else out
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", f"{FPS / step:g}", "-i", "-",
                           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                           "-movflags", "+faststart", silent], stdin=subprocess.PIPE)
    with Pool(4, initializer=init_worker) as pool:
        for k, buf in enumerate(pool.imap(render, frames, chunksize=6)):
            ff.stdin.write(buf)
            if k % 300 == 0:
                print(f"  {k}/{len(frames)}", flush=True)
    ff.stdin.close()
    ff.wait()
    youtube_description(timeline.chapters, os.path.join(os.path.dirname(os.path.abspath(out)),
                                                         "youtube_description.txt"))
    if timeline.cues:
        from narrate import mix, srt
        srt(timeline.cues, os.path.splitext(out)[0] + ".srt")
        wav = out + ".narration.wav"
        mix(timeline.cues, total, wav)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav, "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000",
                        "-c:a", "aac", "-b:a", "160k", "-t", f"{total:.3f}",
                        "-movflags", "+faststart", out], check=True)
        os.remove(silent)
        os.remove(wav)
    print("wrote", out)


if __name__ == "__main__":
    main()
