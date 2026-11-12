#!/usr/bin/env python3
"""RC low-pass filter em ASCII, no estilo de simple-circuit-current.

Autoral (nao vem do ascii-magic): mesmo card 96x30, fios laranja, eletrons
azuis, setas de corrente, painel de dados e rodape do simple-circuit-current,
mas com a topologia da imagem de referencia: fonte v(t), 6k -> no v_C (100uF
ao terra) -> 4k -> no v_o, 8k ao terra.

Loop exato: eletrons andam 8 celulas/s e as setas uma "casa" por periodo,
entao o frame final emenda no inicial sem salto.
"""
import math
from pathlib import Path

sys_path = str(Path(__file__).parent)
import sys

sys.path.insert(0, sys_path)
from gen_svg import build

COLS, ROWS = 96, 30
PER = 3.0          # segundos por ciclo
SETS = 24          # fps
FRAMES = round(PER * SETS)
OUT = "rc-filter/rc-filter.svg"

# paleta identica a peca original (+ roxo do capacitor)
BG = ["#06100c", "#0a1812", "#0e2018", "#12281e"]
WIRE = "#e09a4a"
EL = ["#4ab0ff", "#c8e8ff"]
CUR = "#ffd166"
RES = "#c8a07a"
UI0, UI1, UI3, UI4 = "#ffffff", "#8b949e", "#7ee787", "#ff7b72"
BAT1, BAT2 = "#ff5a4a", "#5a8aff"
CAP = "#a78bfa"

# geometria (mesmas medidas do original: rails e margens)
T, B, L, RB = 4, 24, 8, 70   # topo, base, ramo esquerdo, ramo direito
CAPX = 30                    # ramo do capacitor
END = 86                     # x do terminal ○


def _h(x, y):
    n = math.sin(x * 12.9898 + y * 78.233 + 23) * 43758.5453
    return n - math.floor(n)


def _vnoise(x, y):
    xi, yi = math.floor(x), math.floor(y)
    xf, yf = x - xi, y - yi
    u, v = xf * xf * (3 - 2 * xf), yf * yf * (3 - 2 * yf)
    a, b = _h(xi, yi), _h(xi + 1, yi)
    c, d = _h(xi, yi + 1), _h(xi + 1, yi + 1)
    return a * (1 - u) * (1 - v) + b * u * (1 - v) + c * (1 - u) * v + d * u * v


def fbm(x, y):
    return (_vnoise(x, y) + 0.5 * _vnoise(x * 2, y * 2) + 0.25 * _vnoise(x * 4, y * 4)) / 1.75


def make_frame(ph):
    g = [[None] * COLS for _ in range(ROWS)]

    def put(x, y, ch, fg):
        if 0 <= x < COLS and 0 <= y < ROWS:
            g[y][x] = (ch, fg)

    def text(x, y, s, fg):
        for i, ch in enumerate(s):
            put(x + i, y, ch, fg)

    # fundo texturizado (mesmo algoritmo: fbm + "+" esparso)
    for y in range(ROWS):
        for x in range(COLS):
            n = fbm(x * 0.1, y * 0.25)
            ch = "+" if (x + y * 3) % 7 == 0 else ("▒" if n > 0.6 else "░")
            put(x, y, ch, BG[min(3, int(n * 4))])

    # trilhos com terminais
    for x in range(L, END):
        put(x, T, "━", WIRE)
        put(x, B, "━", WIRE)
    put(L, T, "┏", WIRE); put(L, B, "┗", WIRE)
    put(CAPX, T, "┳", WIRE); put(CAPX, B, "┻", WIRE)
    put(RB, T, "┳", WIRE); put(RB, B, "┻", WIRE)
    put(END, T, "○", UI1); put(END, B, "○", UI1)
    put(END + 2, T, "+", UI0); put(END + 2, B, "−", UI0)

    # ramo esquerdo (fonte v(t))
    for y in range(T + 1, B):
        put(L, y, "┃", WIRE)
    for y in range(12, 17):
        put(L, y, " ", WIRE)

    # ramo do capacitor x=CAPX
    for y in range(T + 1, B):
        put(CAPX, y, "┃", WIRE)
    for x in range(CAPX - 4, CAPX + 5):
        put(x, 13, "━", CAP)
        put(x, 15, "━", CAP)
    put(CAPX, 14, " ", CAP)  # gap entre as placas

    # ramo direito x=RB com o resistor de 8k
    for y in range(T + 1, B):
        put(RB, y, "┃", WIRE)
    for i, y in enumerate(range(13, 19)):
        put(RB, y, "╲" if i % 2 == 0 else "╱", RES)

    # resistores no trilho de cima
    text(14, T, "┤╱╲╱╲╱╲╱╲╱╲├", RES)   # 6 kΩ
    text(48, T, "┤╱╲╱╲╱╲╱╲╱╲├", RES)   # 4 kΩ
    text(16, T + 1, "6 kΩ", UI1)
    text(50, T + 1, "4 kΩ", UI1)

    # bateria (glifo identico ao original)
    text(L - 3, 12, "━━━━━━━", BAT1)
    text(L - 1, 13, "━━━", BAT2)
    text(L - 3, 15, "━━━━━━━", BAT1)
    text(L - 1, 16, "━━━", BAT2)
    text(L + 5, 12, "+", BAT1)
    text(L + 5, 16, "-", BAT2)
    text(L - 6, 14, "v(t)", UI0)

    # rotulos
    text(18, 12, "v_C(t)", UI0)
    text(24, 17, "100 µF", UI1)
    text(RB + 2, 15, "8 kΩ", UI1)
    text(END - 8, 2, "v_o(t)", UI0)

    # painel de dados (mesma caixa do original)
    MX, MY, MW, MH = 36, 9, 30, 9
    put(MX, MY, "╭", UI1); put(MX + MW - 1, MY, "╮", UI1)
    put(MX, MY + MH - 1, "╰", UI1); put(MX + MW - 1, MY + MH - 1, "╯", UI1)
    for x in range(MX + 1, MX + MW - 1):
        put(x, MY, "─", UI1); put(x, MY + MH - 1, "─", UI1)
    for y in range(MY + 1, MY + MH - 1):
        put(MX, y, "│", UI1); put(MX + MW - 1, y, "│", UI1)
    text(MX + 2, MY + 1, f"{'R1':<10}{'6 kΩ':>10}", UI0)
    text(MX + 2, MY + 2, f"{'R2':<10}{'4 kΩ':>10}", UI0)
    text(MX + 2, MY + 3, f"{'R3':<10}{'8 kΩ':>10}", UI0)
    text(MX + 2, MY + 4, f"{'C':<10}{'100 µF':>10}", UI0)
    text(MX + 2, MY + 5, "Fc = 1/(2πRC)", UI1)
    text(MX + 2, MY + 6, "low-pass filter", UI3)

    # legenda (mesmas linhas do original)
    text(1, 27, "● electrons drift from - to +", EL[1])
    text(33, 27, "→ conventional current flows from + to -", CUR)
    text(1, 28, "the capacitor smooths the output; electron drift is really under a millimetre per second", UI1)
    text(1, 0, "AN RC LOW-PASS FILTER", UI0)

    # caminho do laco (horario): topo -> direita -> base -> esquerda
    path = ([(x, T) for x in range(L, RB)] + [(RB, y) for y in range(T, B)]
            + [(x, B) for x in range(RB, L, -1)] + [(L, y) for y in range(B, T, -1)])
    n = len(path)
    # eletrons: 8 celulas/s; sobre PER da 8*3=24 = multiplo do espacamento (4)
    drift = ph * 8
    for k in range(0, n, 4):
        x, y = path[int(((n - 1 - k - drift) % n + n) % n)]
        if g[y][x] and g[y][x][0] in ("━", "┃"):
            put(x, y, "●", EL[0] if (k >> 2) % 3 else EL[1])
    # setas: uma "casa" de seta por periodo -> loop exato
    for k in range(6):
        i = int(((k / 6 + ph / PER) % 1) * n)
        x, y = path[i]
        nx, ny = path[(i + 1) % n]
        ch = "→" if nx > x else "←" if nx < x else "↓" if ny > y else "↑"
        ox = -2 if x == L else 2 if x == RB else 0
        oy = -1 if y == T else 1 if y == B else 0
        put(x + ox, y + oy, ch, CUR)
    return g


def main():
    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    sel = []
    for i in range(FRAMES):
        g = make_frame(i * PER / FRAMES)
        fr = [[(ch, fg) for ch, fg in row] for row in g]
        chars = ["".join(ch for ch, _ in row) for row in fr]
        sel.append((fr, chars))
    build(sel, OUT, PER)
    assert len(sel) == FRAMES
    print(f"ok: {FRAMES} frames, loop {PER}s, drift 8 cel/s, setas 1 casa/periodo")


if __name__ == "__main__":
    main()
