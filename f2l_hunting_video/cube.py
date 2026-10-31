"""Minimal 3x3 cube model: cubies with orientation matrices, standard move notation."""
import numpy as np

# Axes: x = Right, y = Up, z = Front.  Standard colour scheme, white on bottom.
FACE_COLORS = {
    (0, 1, 0): "Y", (0, -1, 0): "W",
    (0, 0, 1): "G", (0, 0, -1): "B",
    (1, 0, 0): "R", (-1, 0, 0): "O",
}

# move letter -> (axis index, layer selector value or None for whole cube, angle sign)
MOVES = {
    "R": (0, 1, -1), "L": (0, -1, 1),
    "U": (1, 1, -1), "D": (1, -1, 1),
    "F": (2, 1, -1), "B": (2, -1, 1),
    "y": (1, None, -1),
}


def rot(axis, angle):
    c, s = np.cos(angle), np.sin(angle)
    if axis == 0:
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == 1:
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def parse(alg):
    """'R U2 R\'' -> [('R', 1), ('U', 2), ('R', -1)]"""
    out = []
    for tok in alg.split():
        base, mod = tok[0], tok[1:]
        n = {"": 1, "'": -1, "2": 2, "2'": 2}[mod]
        out.append((base, n, tok))
    return out


def invert(alg):
    inv = []
    for base, n, _ in reversed(parse(alg)):
        inv.append(base + ("2" if n == 2 else ("'" if n == 1 else "")))
    return " ".join(inv)


class Cubie:
    def __init__(self, home):
        self.home = np.array(home, dtype=float)
        self.M = np.eye(3)
        self.stickers = []  # (home normal, colour letter)
        for i in range(3):
            if home[i] != 0:
                n = [0, 0, 0]
                n[i] = home[i]
                self.stickers.append((np.array(n, dtype=float), FACE_COLORS[tuple(n)]))

    @property
    def pos(self):
        return self.M @ self.home

    def kind(self):
        return int(np.count_nonzero(self.home))  # 1 centre, 2 edge, 3 corner


class Cube:
    def __init__(self):
        self.cubies = [Cubie((x, y, z)) for x in (-1, 0, 1) for y in (-1, 0, 1)
                       for z in (-1, 0, 1) if (x, y, z) != (0, 0, 0)]

    def layer(self, base):
        axis, sel, _ = MOVES[base]
        if sel is None:
            return list(self.cubies)
        return [c for c in self.cubies if round(c.pos[axis]) == sel]

    def angle(self, base, n):
        return MOVES[base][2] * n * np.pi / 2

    def apply(self, base, n):
        axis = MOVES[base][0]
        R = np.round(rot(axis, self.angle(base, n)))
        for c in self.layer(base):
            c.M = np.round(R @ c.M)

    def run(self, alg):
        for base, n, _ in parse(alg):
            self.apply(base, n)
        return self

    def find(self, home):
        for c in self.cubies:
            if tuple(c.home) == tuple(home):
                return c

    def snapshot(self):
        return [c.M.copy() for c in self.cubies]

    def restore(self, snap):
        for c, M in zip(self.cubies, snap):
            c.M = M.copy()

    def solved_except_u(self):
        """True if every cubie outside the U layer is home and correctly oriented."""
        for c in self.cubies:
            if c.home[1] == 1:
                continue
            if not np.allclose(c.M @ c.home, c.home):
                return False
            for n, _ in c.stickers:
                if not np.allclose(c.M @ n, n):
                    return False
        return True


NAMES = {(0, 1, 0): "U", (0, -1, 0): "D", (0, 0, 1): "F", (0, 0, -1): "B", (1, 0, 0): "R", (-1, 0, 0): "L"}


def describe(cube, home):
    c = cube.find(home)
    p = np.round(c.pos).astype(int)
    loc = "".join(NAMES[tuple(int(v) if j == i else 0 for j, v in enumerate(p))]
                  for i in (1, 2, 0) if p[i] != 0)
    faces = {col: NAMES[tuple(np.round(c.M @ n).astype(int))] for n, col in c.stickers}
    return loc, faces
