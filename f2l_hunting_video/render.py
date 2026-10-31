"""Render the F2L Hunting Story video (3D animated cube + story captions) to MP4.

Usage:  python3 render.py [out.mp4] [--preview N]   (--preview renders only every Nth frame)
"""
import math
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

FONT_DIR = "/usr/share/fonts/opentype/inter/"
_fonts = {}


def font(size, weight="Bold"):
    key = (size, weight)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(f"{FONT_DIR}Inter-{weight}.otf", size * SS)
    return _fonts[key]


RGB = {
    "W": (245, 245, 245), "Y": (255, 213, 0), "G": (0, 170, 80),
    "B": (20, 90, 220), "R": (215, 30, 40), "O": (255, 120, 0),
}
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


def wrap(txt, f, width):
    lines = []
    for para in txt.split("\n"):
        cur = ""
        for word in para.split():
            trial = (cur + " " + word).strip()
            if text_w(trial, f) > width and cur:
                lines.append(cur)
                cur = word
            else:
                cur = trial
        lines.append(cur)
    return lines


def pill(draw, x, y, txt, f, fill, color=(255, 255, 255), pad=(14, 6), anchor_center=False):
    w = text_w(txt, f) + pad[0] * 2
    h = f.size / SS + pad[1] * 2 + 2
    if anchor_center:
        x -= w / 2
    draw.rounded_rectangle(S(x, y, x + w, y + h), radius=int(h * SS / 2), fill=fill)
    draw.text(S(x + pad[0], y + pad[1] - 1), txt, font=f, fill=color)
    return w, h


def tag(draw, anchor, txt, fill, color, side):
    """Label with a leader line pointing at a piece."""
    ax, ay = anchor
    f = font(17)
    w = text_w(txt, f) + 24
    h = 30
    tx = ax + (70 if side > 0 else -70 - w)
    ty = ay - 75
    draw.line(S(ax, ay, tx + (0 if side > 0 else w), ty + h / 2), fill=fill, width=3 * SS)
    draw.ellipse(S(ax - 6, ay - 6, ax + 6, ay + 6), fill=fill, outline=(0, 0, 0), width=2 * SS)
    pill(draw, tx, ty, txt, f, fill, color, pad=(12, 5))


def alg_bar(draw, fr, y):
    toks, chunks = fr["alg_tokens"], fr.get("alg_chunks")
    cur, done = fr.get("alg_cur", -1), fr.get("alg_done", 0)
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
            fill, tc, ol = (255, 205, 0), (20, 16, 30), (255, 230, 120)
        elif i < done:
            fill, tc, ol = (40, 120, 70), (220, 255, 230), None
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
        col = (255, 205, 0) if ci == active_chunk else (150, 140, 190)
        draw.line(S(x0 + 4, y + 64, x1 - 4, y + 64), fill=col, width=3 * SS)
        lw = text_w(label, fl)
        draw.text(S((x0 + x1) / 2 - lw / 2, y + 72), label, font=fl, fill=col)


def pop_text(draw, txt, t, color):
    """Big centred word that pops in (t in 0..1 over its lifetime)."""
    sc = min(1.0, t * 5) if t < 0.2 else 1.0
    size = int(64 * (0.6 + 0.4 * sc))
    f = font(size, "Black") if _has_black() else font(size)
    w = text_w(txt, f)
    x, y = 880 - w / 2, 70
    for dx, dy in ((3, 3), (-2, 2)):
        draw.text(S(x + dx, y + dy), txt, font=f, fill=(0, 0, 0))
    draw.text(S(x, y), txt, font=f, fill=color)


def _has_black():
    import os
    return os.path.exists(f"{FONT_DIR}Inter-Black.otf")


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
            for home, txt, fill, tcol, side in ((HUNTER, "HUNTER", (255, 255, 255), (20, 16, 30), 1),
                                                 (PREY, "PREY", (255, 140, 30), (20, 16, 30), -1)):
                i = idx[home]
                p = V @ (mats[i] @ cube.cubies[i].home)
                tag(draw, project(p, cx, cy, scale), txt, fill, tcol, side)
        if fr.get("den_tag"):
            p = V @ np.array([1.0, -0.5, 1.0])
            tag(draw, project(p, cx, cy, scale), "DEN (empty slot)", (120, 200, 255), (10, 20, 40), 1)

    if kind == "title":
        a = fr.get("alpha", 1)
        c = tuple(int(255 * a) for _ in range(3))
        draw.text(S(70, 170), "F2L", font=font(120), fill=(255, 205, 0))
        draw.text(S(70, 305), "THE HUNTING", font=font(64), fill=c)
        draw.text(S(70, 380), "STORY", font=font(64), fill=c)
        pill(draw, 70, 480, "11 CASES", font(22), (240, 110, 30))
        pill(draw, 210, 480, "5 CHAPTERS", font(22), (150, 60, 200))
        pill(draw, 385, 480, "3D ANIMATED", font(22), (70, 140, 240))
        draw.text(S(70, 560), "Learn intuitive F2L as a story: a hunter, its prey, and a den.",
                  font=font(20, "Medium"), fill=(200, 195, 220))
        draw.text(S(70, 590), "Story idea inspired by RiDo's \"Hunting Story for F2L\".",
                  font=font(16, "Regular"), fill=(150, 145, 170))

    if kind in ("intro", "case", "rules", "outro"):
        if fr.get("chip"):
            pill(draw, 50, 34, fr["chip"], font(18), fr.get("chip_color", (150, 60, 200)))
        if fr.get("title"):
            draw.text(S(50, 80), fr["title"], font=font(40), fill=(255, 255, 255))
        if fr.get("subtitle"):
            draw.text(S(52, 132), fr["subtitle"], font=font(19, "Medium"), fill=(190, 180, 220))

    if fr.get("caption"):
        f = font(25, "SemiBold")
        lines = wrap(fr["caption"], f, 470)
        y0 = 190
        h = len(lines) * 36 + 30
        draw.rounded_rectangle(S(40, y0, 540, y0 + h), radius=18 * SS, fill=(30, 24, 48),
                               outline=(90, 75, 130), width=2 * SS)
        draw.rectangle(S(40, y0 + 14, 46, y0 + h - 14), fill=(255, 205, 0))
        for k, ln in enumerate(lines):
            draw.text(S(64, y0 + 15 + k * 36), ln, font=f, fill=(255, 255, 255))

    if fr.get("bullets"):
        y = fr.get("bullets_y", 190)
        for head, body in fr["bullets"]:
            draw.text(S(50, y), head, font=font(23), fill=(255, 205, 0))
            fb = font(20, "Medium")
            hw = text_w(head, font(23)) + 12
            lines = wrap(body, fb, 560 - hw)
            for k, ln in enumerate(lines):
                draw.text(S(50 + hw, y + 2 + k * 28), ln, font=fb, fill=(235, 230, 245))
            y += max(1, len(lines)) * 28 + 18

    if fr.get("table"):
        y = 150
        for name, alg, note in fr["table"]:
            draw.rounded_rectangle(S(60, y, 1220, y + 70), radius=14 * SS, fill=(30, 24, 48))
            draw.text(S(84, y + 10), name, font=font(24), fill=(255, 205, 0))
            draw.text(S(84, y + 40), note, font=font(17, "Medium"), fill=(190, 180, 220))
            draw.text(S(560, y + 18), alg, font=font(28), fill=(255, 255, 255))
            y += 84

    if fr.get("footer"):
        draw.text(S(60, 600), fr["footer"], font=font(22, "SemiBold"), fill=(120, 200, 255))

    if fr.get("alg_tokens"):
        alg_bar(draw, fr, 600)

    if fr.get("pop"):
        txt, t, color = fr["pop"]
        pop_text(draw, txt, t, color)

    if fr.get("speed_label"):
        pill(draw, 1100, 34, fr["speed_label"], font(16), (60, 50, 90))

    return img.resize((W, H), Image.LANCZOS).tobytes()


CUBE = None


def init_worker():
    global BG, CUBE
    BG = make_background()
    CUBE = Cube()


def main():
    out = "f2l_hunting_story.mp4"
    step = 1
    args = sys.argv[1:]
    if "--preview" in args:
        step = int(args[args.index("--preview") + 1])
        args = [a for a in args if a not in ("--preview", str(step))]
    if args:
        out = args[0]
    frames = build_timeline(FPS)[::step]
    print(f"{len(frames)} frames, {len(frames) / FPS * step:.1f}s", flush=True)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS // step if step > 1 else FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                           "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    with Pool(4, initializer=init_worker) as pool:
        for k, buf in enumerate(pool.imap(render, frames, chunksize=6)):
            ff.stdin.write(buf)
            if k % 300 == 0:
                print(f"  {k}/{len(frames)}", flush=True)
    ff.stdin.close()
    ff.wait()
    print("wrote", out)


if __name__ == "__main__":
    main()
