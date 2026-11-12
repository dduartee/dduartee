#!/usr/bin/env python3
"""Exemplo 7.7 resolvido e animado: resposta do RC low-pass ao pulso de 9 V.

Mesmo card/estilo do gen_rc_filter (autoral). Circuito a esquerda, plot de
v_o(t) a direita (a curva desenha conforme a simulacao avanca) e a resolucao
no painel: tau = 4k*100uF = 0,4 s; carga v_o = 4(1-e^-t/0.4); em 0,3 s vale
2,11 V; depois descarrega com o "novo 0".
"""
import math
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parent))
from gen_svg import build
from gen_rc_filter import (BG, WIRE, EL, CUR, RES, UI0, UI1, UI3, UI4,
                           BAT1, BAT2, CAP, fbm)

COLS, ROWS = 96, 30
FPS = 24
LOOP = 4.5          # s de parede
DRAW = 4.0          # s de parede desenhando (t_sim 0 -> 1.5)
T_END = 1.5         # s de simulacao
FRAMES = round(LOOP * FPS)
OUT = "rc-pulse/rc-pulse.svg"

T, B, L, RB = 7, 17, 6, 36   # circuito (dimensoes compactas)
CAPX, END = 20, 40
AX, AY = 50, 16              # eixos do plot
X0, X1 = 52, 92              # colunas da curva
Y0, Y1 = 5, 16               # 4 V (topo) e 0 V (base)
C03 = 60                     # coluna de t = 0,3 s
TAU = 0.4


def vo(t):
    if t < 0.3:
        return 4 * (1 - math.exp(-t / TAU))
    return 4 * (1 - math.exp(-0.3 / TAU)) * math.exp(-(t - 0.3) / TAU)


def vc(t):
    """Tensao no capacitor: carga ate 6 V com a fonte em 9 V, descarga depois."""
    if t < 0.3:
        return 6 * (1 - math.exp(-t / TAU))
    return 6 * (1 - math.exp(-0.3 / TAU)) * math.exp(-(t - 0.3) / TAU)


def make_frame(ph):
    g = [[None] * COLS for _ in range(ROWS)]

    def put(x, y, ch, fg):
        if 0 <= x < COLS and 0 <= y < ROWS:
            g[y][x] = (ch, fg)

    def text(x, y, s, fg):
        for i, ch in enumerate(s):
            put(x + i, y, ch, fg)

    for y in range(ROWS):
        for x in range(COLS):
            n = fbm(x * 0.1, y * 0.25)
            ch = "+" if (x + y * 3) % 7 == 0 else ("▒" if n > 0.6 else "░")
            put(x, y, ch, BG[min(3, int(n * 4))])

    # estado da simulacao neste frame: fonte ligada (9 V) ate 0,3 s
    t_sim = T_END * min(1.0, ph / DRAW)
    on = t_sim < 0.3
    vct = vc(t_sim)

    # --- circuito ---
    for x in range(L, END):
        put(x, T, "━", WIRE)
        put(x, B, "━", WIRE)
    put(L, T, "┏", WIRE); put(L, B, "┗", WIRE)
    put(CAPX, T, "┳", WIRE); put(CAPX, B, "┻", WIRE)
    put(RB, T, "┳", WIRE); put(RB, B, "┻", WIRE)
    put(END, T, "○", UI1); put(END, B, "○", UI1)
    put(END + 2, T, "+", UI0); put(END + 2, B, "−", UI0)
    for y in range(T + 1, B):
        put(L, y, "┃", WIRE)
        put(CAPX, y, "┃", WIRE)
        put(RB, y, "┃", WIRE)
    for y in range(11, 16):
        put(L, y, " ", WIRE)
    # resistores (8 celulas) e o de 8k vertical
    text(10, T, "┤╱╲╱╲╱├", RES)
    text(24, T, "┤╱╲╱╲╱├", RES)
    text(11, T + 1, "6 kΩ", UI1)
    text(25, T + 1, "4 kΩ", UI1)
    for i, y in enumerate(range(12, 16)):
        put(RB, y, "╲" if i % 2 == 0 else "╱", RES)
    text(RB + 5, 13, "8 kΩ", UI1)
    # capacitor
    for x in range(CAPX - 2, CAPX + 3):
        put(x, 12, "━", CAP)
        put(x, 14, "━", CAP)
    put(CAPX, 13, " ", CAP)
    # eletrons armazenados na placa de baixo (cresce com v_C, drena na descarga)
    for i in range(round(vct / 6 * 5)):
        put(CAPX - 2 + i, 14, "●", EL[1])
    text(8, 13, f"v_C={vct:.2f}V".replace(".", ","), CAP)
    text(CAPX - 7, 15, "100 µF", UI1)
    # bateria v(t): apagada quando a fonte esta em 0 V (pulso terminou)
    b1, b2 = (BAT1, BAT2) if on else (UI1, UI1)
    text(L - 3, 11, "━━━━━━━", b1)
    text(L - 1, 12, "━━━", b2)
    text(L - 3, 14, "━━━━━━━", b1)
    text(L - 1, 15, "━━━", b2)
    text(L + 5, 11, "+", b1)
    text(L + 5, 15, "-", b2)
    text(0, 5, f"v(t) = {9.0 if on else 0.0:.1f} V".replace(".", ","), b1)

    # --- plot ---
    put(AX, AY, "└", UI1)
    for y in range(Y0, AY):
        put(AX, y, "│", UI1)
    for x in range(AX + 1, COLS - 1):
        put(x, AY, "─", UI1)
    put(COLS - 1, AY, "→", UI1)
    text(47, 5, "4V", UI1)
    text(46, 10, "2,11", UI1)
    text(51, 17, "0", UI1)
    text(58, 17, "0,3", UI1)
    text(88, 17, "t(s)", UI1)
    text(X0, 3, "v_o(t)", UI0)
    for x in range(X0, COLS - 1):
        put(x, Y0, "┈", UI1)          # guia 4 V
    for x in range(X0, C03):
        put(x, 10, "┈", UI1)          # guia 2,11 V
    for y in range(11, AY):
        put(C03, y, "┆", UI1)         # guia t = 0,3 s
    put(C03, 10, "●", UI3)

    # tempo de simulacao ja calculado acima; desenha a curva ate t_sim
    prev_v = 0.0
    for c in range(X1 - X0 + 1):
        t = c / (X1 - X0) * T_END
        if t > t_sim:
            break
        v = vo(t)
        row = AY - round(v / 4 * (AY - Y0))
        ch = "╱" if v > prev_v + 0.02 else "╲" if v < prev_v - 0.02 else "─"
        if not (t >= 0.28 and t <= 0.32):
            put(X0 + c, row, ch, BAT1)
        prev_v = v
    text(C03 - 4, 19, "novo 0", UI3)
    put(C03, 18, "▲", UI3)

    # leituras vivas
    text(52, 4, f"t = {t_sim:4.2f} s".replace(".", ","), UI0)
    text(76, 4, f"v_o = {vo(t_sim):4.2f} V".replace(".", ","), UI0)

    # --- resolucao ---
    text(1, 20, "v(t) ─┐███████└──────────  9 V em 0 ≤ t < 0,3 s", UI1)
    for x in range(8, 15):
        put(x, 20, "█", BAT1)
    text(1, 21, "τ = Rth · C = 4 kΩ · 100 µF = 0,4 s", UI0)
    text(1, 22, "v_o(t) = 4 (1 − e^(−t/0,4))   for 0 ≤ t < 0,3 s", UI0)
    text(1, 23, "v_o(0,3) = 4 (1 − e^(−0,3/0,4)) = 2,11 V", UI3)
    text(1, 24, "t ≥ 0,3 s:  v_o(t) = 2,11 · e^(−(t − 0,3)/0,4)", UI0)

    # legenda e titulo
    text(1, 27, "● electrons drift from - to +", EL[1])
    text(33, 27, "→ conventional current flows from + to -", CUR)
    text(1, 28, "the capacitor smooths the output; electron drift is really under a millimetre per second", UI1)
    text(1, 0, "RC LOW-PASS: PULSE RESPONSE (EX. 7.7)", UI0)

    # eletrons e setas no laco; sentidos invertem na descarga (fonte em 0 V)
    path = ([(x, T) for x in range(L, RB)] + [(RB, y) for y in range(T, B)]
            + [(x, B) for x in range(RB, L, -1)] + [(L, y) for y in range(B, T, -1)])
    n = len(path)
    drift = ph * 8 * (1 if on else -1)
    for k in range(0, n, 4):
        x, y = path[int(((n - 1 - k - drift) % n + n) % n)]
        if g[y][x] and g[y][x][0] in ("━", "┃"):
            put(x, y, "●", EL[0] if (k >> 2) % 3 else EL[1])
    for k in range(6):
        i = int(((k / 6 + ph / LOOP) % 1) * n)
        x, y = path[i]
        nx, ny = path[(i + 1) % n if on else (i - 1) % n]  # corrente convencional inverte
        ch = "→" if nx > x else "←" if nx < x else "↓" if ny > y else "↑"
        ox = -2 if x == L else 2 if x == RB else 0
        oy = -1 if y == T else 1 if y == B else 0
        put(x + ox, y + oy, ch, CUR)
    # eletrons no ramo do capacitor: sobem na carga, descem na descarga
    branch = [16, 15, 11, 10, 9, 8]   # baixo -> cima, fora das placas
    sgn = 1 if on else -1
    for j in range(2):
        idx = int((j * len(branch) / 2 + ph * 4 * sgn) % len(branch))
        put(CAPX, branch[idx], "●", EL[0])
    return g


def main():
    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    sel = []
    for i in range(FRAMES):
        g = make_frame(i * LOOP / FRAMES)
        fr = [[(ch, fg) for ch, fg in row] for row in g]
        chars = ["".join(ch for ch, _ in row) for row in fr]
        sel.append((fr, chars))
    build(sel, OUT, LOOP)
    assert len(sel) == FRAMES
    v03 = vo(0.3)
    assert abs(v03 - 2.11) < 0.01, v03
    print(f"ok: {FRAMES} frames, loop {LOOP}s; v_o(0,3) = {v03:.2f} V")


if __name__ == "__main__":
    main()
