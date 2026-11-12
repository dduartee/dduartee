#!/usr/bin/env python3
"""Filtro RC hand-made -> SVG animado (mesmo estilo dos cards do ascii-magic).

Fonte quadrada 5 V (periodo 2.4 s) -> capacitor carregando/descarregando com
tau = (6k + 4k||8k) * 100uF = 0.867 s. Osciloscopio rola as traces de v(t) e
v_C(t); leituras de v_C, v_o e corrente por frame.

Uso: python3 tools/gen_rc_card.py
Escreve rc-filter/rc-filter.svg + rc-filter/README.md.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gen_svg import esc, merge_runs  # noqa: E402

FS, ADV, LH = 13, 7.8, 15.6
PAD_X, PAD_Y = 20, 16
BG = "#292724"
FPS = 20
LOOP = 2.4          # periodo da fonte quadrada (s)
R_SRC = 6_000       # serie
R_DIV = 4_000 * 8_000 / (4_000 + 8_000)  # 4k || 8k
TAU = (R_SRC + R_DIV) * 100e-6           # 0.867 s
VIN = 5.0
COLS = 72

COLORS = {
    "a": "#e3b341", "w": "#d0d0c8", "d": "#8b949e", "b": "#58a6ff",
    "r": "#f85149", "p": "#bc8cff", "g": "#3fb950", "c": "#79c0ff",
}


def parse(markup):
    """'<a>texto</><w>...' -> lista de (char, cor|None)."""
    cells, cur = [], None
    i = 0
    while i < len(markup):
        if markup[i] == "<" and i + 2 < len(markup) and (markup[i + 1] in COLORS or markup[i + 1] == "/"):
            if markup[i + 2] == ">":
                cur = None if markup[i + 1] == "/" else COLORS[markup[i + 1]]
                i += 3
                continue
        cells.append((markup[i], cur))
        i += 1
    return cells


def vc_at(t):
    """v_C(t) em regime permanente do chaveamento (1.00 V .. 4.00 V)."""
    a = math.exp(-1.2 / TAU)
    vmax = VIN / (1 + a)
    t = t % LOOP
    if t < 1.2:  # carga a partir de vmin
        return vmin(a) + (vmax - vmin(a)) * (1 - math.exp(-t / TAU))
    return vmax * math.exp(-(t - 1.2) / TAU)


def vmin(a):
    return VIN / (1 + a) * a


def scope_row(value, rows, lo, hi):
    """valor -> linha (0 = topo)."""
    f = (value - lo) / (hi - lo)
    f = min(1.0, max(0.0, f))
    return rows - 1 - round(f * (rows - 1))


def frame_markup(t):
    vc = vc_at(t)
    vo = vc * 8.0 / 12.0
    cur = (VIN if t % LOOP < 1.2 else 0.0) - vc
    i_ma = abs(cur) / (R_SRC + R_DIV) * 1000
    state = "charging ↑" if t % LOOP < 1.2 else "discharging ↓"

    # osciloscopio: janela de LOOP s, 54 colunas, 6 linhas; celula a celula
    sw, srows = 54, 6
    grid = [[(" ", None)] * sw for _ in range(srows)]
    prev_r = None
    for c in range(sw):
        tt = (t - (sw - 1 - c) / sw * LOOP) % LOOP
        r = scope_row(VIN if tt < 1.2 else 0.0, srows, 0, VIN)
        if prev_r is not None and r != prev_r:  # transicao do quadrado
            for rr in range(min(prev_r, r) + 1, max(prev_r, r)):
                grid[rr][c] = ("│", COLORS["d"])
        grid[r] = list(grid[r])
        grid[r][c] = ("─", COLORS["d"])
        prev_r = r
    for c in range(sw):
        tt = (t - (sw - 1 - c) / sw * LOOP) % LOOP
        rr = scope_row(vc_at(tt), srows, 0, VIN)
        grid[rr][c] = ("█", COLORS["g"])
    rev = {v: k for k, v in COLORS.items()}

    def markup(cells):
        out, cur = "", None
        for ch, col in cells:
            if col != cur:
                if cur:
                    out += "</>"
                if col:
                    out += f"<{rev[col]}>"
                cur = col
            out += ch
        return out + ("</>" if cur else "")

    scope = [markup(row) for row in grid]

    return [
        f"<a>  RC LOW-PASS FILTER</>                                             <d>first order</>",
        "",
        "      <w>┌──────</><b>/\\/\\/\\</><w>──────┬──────</><b>/\\/\\/\\</><w>──────┬─────o <d>v_o(t) +</>",
        "      <w>│</>      <d>6 kΩ</>       <w>│</>      <d>4 kΩ</>       <w>│</>",
        "      <w>│</>                 <w>│</>                  <w>│</>",
        "     <r>(+)</>                <w>│</>                <b>/\\/\\/\\</>",
        "   <r>( v(t) )</>            <w>──</><p>┴</><w>──</>              <d>8 kΩ</>",
        "     <r>(−)</> <d>5 V</>          <w>──</><p>┬</><w>──</> <p>100 µF</>      <b>/\\/\\/\\</>",
        "      <w>│</>                <d>v_C(t)</>              <w>│</>",
        "      <w>└──────────────────┴──────────────────┴─────o</> <d>v_o(t) −</>",
        "",
        "   <d>┌──────────────────────────────────────────────────────┐</>",
        *[f"   <d>│</> {s}<d>│</>" for s in scope],
        "   <d>└──────────────────────────────────────────────────────┘</>",
        "   <d>──</> <d>v(t)</> <d>entrada 5 V</>   <g>──</> <g>v_C(t)</> <g>capacitor 100 µF</>   <d>τ = 0.87 s</>",
        "",
        f"   t = <a>{t:5.2f} s</>    v_C = <a>{vc:4.2f} V</>    v_o = <a>{vo:4.2f} V</>    i = <a>{i_ma:4.2f} mA</>   <g>{state}</>",
    ]


def build(rows):
    """rows = lista de linhas; cada linha = lista de células (char, cor).
    Imprime linhas estáticas uma vez e as dinâmicas por frame."""
    W = round(len(rows[0][0]) * ADV + 2 * PAD_X)
    H = round(len(rows[0]) * LH + 2 * PAD_Y)
    fill_ids = {}

    def tspans(line):
        body = ""
        for t, fg in merge_runs(line):
            t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if fg:
                cid = fill_ids.setdefault(fg, f"c{len(fill_ids)}")
                body += f'<tspan class="{cid}">{t}</tspan>'
            else:
                body += f"<tspan>{t}</tspan>"
        return body

    nrows = len(rows[0])
    static, dyn = [], []  # dyn[i] = linhas do frame i
    for r in range(nrows):
        if all(rows[f][r] == rows[0][r] for f in range(len(rows))):
            static.append((r, tspans(rows[0][r])))
    static_r = {r for r, _ in static}
    for f, rows_f in enumerate(rows):
        lines = []
        for r in range(nrows):
            if r in static_r:
                continue
            lines.append(f'<text x="{PAD_X}" y="{round(PAD_Y + FS * 0.85 + r * LH)}">{tspans(rows_f[r])}</text>')
        dyn.append(f'<g class="f" style="animation-delay:{round(f * LOOP / len(rows), 4)}s">{"".join(lines)}</g>')

    stat_txt = "".join(
        f'<text x="{PAD_X}" y="{round(PAD_Y + FS * 0.85 + r * LH)}">{body}</text>'
        for r, body in static)
    css = " ".join(f".{cid}{{fill:{fg}}}" for fg, cid in fill_ids.items())
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t">
<title id="t">RC low-pass filter - animated ASCII</title>
<style>
text{{font:{FS}px Menlo,Consolas,"DejaVu Sans Mono","Liberation Mono",monospace;fill:#d0d0c8;white-space:pre}}
{css}
.f{{opacity:0;animation:swap {round(LOOP, 2)}s steps(1,end) infinite}}
@keyframes swap{{0%{{opacity:1}}{round(100 / len(rows), 2)}%{{opacity:0}}100%{{opacity:0}}}}
@media (prefers-reduced-motion:reduce){{.f{{animation:none}}.f:first-of-type{{opacity:1}}}}
</style>
<rect width="{W}" height="{H}" rx="12" fill="{BG}"/>
{stat_txt}
{"".join(dyn)}
</svg>
'''
    out = Path(__file__).parent.parent / "rc-filter" / "rc-filter.svg"
    out.parent.mkdir(exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    rmd = out.parent / "README.md"
    if not rmd.exists():
        rmd.write_text(f"# rc-filter\n\n![rc-filter]({out.name})\n", encoding="utf-8")
    print(f"{out}: {len(rows)} frames, loop {LOOP}s, {nrows} linhas, {W}x{H}px, {len(static)} estaticas")


def main():
    n = round(LOOP * FPS)
    frames = [frame_markup(i * LOOP / n) for i in range(n)]
    grids = [[parse(line) for line in fr] for fr in frames]
    width = max(len(r) for g in grids for r in g)
    for g in grids:  # padrao de largura
        for r in g:
            r.extend([(" ", None)] * (width - len(r)))
    build(grids)


if __name__ == "__main__":
    main()
