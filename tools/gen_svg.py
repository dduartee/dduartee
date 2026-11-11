#!/usr/bin/env python3
"""ascii-magic piece -> SVG animado (frames em <text>, troca via CSS steps).

Uso:
  python3 tools/gen_svg.py rotating-cube --look=lines --out=cube.svg
  python3 tools/gen_svg.py spinning-torus --look=dots --out=torus.svg

Ao sobrescrever um SVG ja referenciado no README, suba o ?v=N na referencia
(nova URL = cache novo). Arquivo novo nao precisa.

O loop e fechado no periodo de rotacao (frame mais parecido com o frame 0,
tolerancia de 3% de chars - o render tem ruido entre passes).
"""
import argparse
import re
import subprocess
import xml.dom.minidom as minidom

ESC = "\x1b"
FS, ADV, LH = 13, 7.8, 15.6
PAD_X, PAD_Y = 20, 16
BG, FG = "#292724", "#e4e4e7"


def capture(piece, look, seconds):
    p = subprocess.run(
        ["npx", "--yes", "ascii-magic-art", piece, f"--look={look}", f"--seconds={seconds}"],
        capture_output=True, timeout=seconds + 15, check=False)
    return p.stdout.decode("utf-8", "replace")


def frames(raw):
    out = []
    for part in raw.split(ESC + "[H"):
        part = re.sub(ESC + r"\[[0-9?]*[a-zA-Z]", "", part)
        lines = [ln.rstrip() for ln in part.splitlines()]
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        if lines:
            out.append(lines)
    uniq = []
    for f in out:
        if not uniq or uniq[-1] != f:
            uniq.append(f)
    return uniq


def ndiff(a, b):
    """Diferenca posicional entre frames normalizados a um grid (celula a celula)."""
    R = max(len(a), len(b))
    C = max(max(len(l) for l in f) for f in (a, b))
    return sum(1 for r in range(R) for c in range(C)
               if (a[r][c] if r < len(a) and c < len(a[r]) else " ")
               != (b[r][c] if r < len(b) and c < len(b[r]) else " "))


def one_period(uniq):
    """Retorna (n_frames_do_periodo, diff) se houver ciclo; None se nao.

    O cubo gira em dois eixos: o pose exato repete longe. Pegamos o j com
    menor diferenca posicional de silhueta (j >= 12 evita poses adjacentes).
    """
    if len(uniq) < 16:
        return None
    filled = sum(1 for l in uniq[0] for ch in l if ch != " ")
    best = min((ndiff(uniq[0], uniq[j]), j) for j in range(12, len(uniq)))
    if best[0] <= 0.25 * filled:
        return best[1], best[0]
    return None


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build(sel, path, loop):
    rows = max(len(f) for f in sel)
    cols = max(max(len(l) for l in f) for f in sel)
    W = round(cols * ADV + 2 * PAD_X)
    H = round(rows * LH + 2 * PAD_Y)
    step = loop / len(sel)
    texts = []
    for i, f in enumerate(sel):
        tsp = "".join(
            f'<tspan x="{PAD_X}" y="{round(PAD_Y + FS * 0.85 + r * LH)}">{esc(ln)}</tspan>'
            for r, ln in enumerate(f))
        texts.append(
            f'<text xml:space="preserve" class="f" style="animation-delay:{round(-i * step, 4)}s">{tsp}</text>')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t">
<title id="t">{esc(path)} - ASCII Magic animation</title>
<style>
text{{font:{FS}px Menlo,Consolas,"DejaVu Sans Mono","Liberation Mono",monospace;fill:{FG};white-space:pre}}
.f{{opacity:0;animation:swap {round(loop, 2)}s steps(1,end) infinite}}
@keyframes swap{{0%{{opacity:1}}{round(100 / len(sel), 2)}%{{opacity:0}}100%{{opacity:0}}}}
@media (prefers-reduced-motion:reduce){{.f{{animation:none}}.f:first-of-type{{opacity:1}}}}
</style>
<rect width="{W}" height="{H}" rx="12" fill="{BG}"/>
{"".join(texts)}
</svg>
'''
    open(path, "w", encoding="utf-8").write(svg)
    n = len(minidom.parse(path).getElementsByTagName("text"))
    assert n == len(sel), f"self-check: {n} text != {len(sel)} frames"
    print(f"{path}: {len(sel)} frames, loop {round(loop, 2)}s, {rows}x{cols} chars, {W}x{H}px")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("piece", help="ex.: rotating-cube (lista: npx ascii-magic-art --list)")
    ap.add_argument("--look", default="lines", help="dots | lines | block (default: lines)")
    ap.add_argument("--out", default=None, help="arquivo de saida (default: <piece>.svg)")
    ap.add_argument("--seconds", type=int, default=6, help="duracao da captura (default: 6)")
    a = ap.parse_args()
    out = a.out or f"{a.piece}.svg"
    uniq = frames(capture(a.piece, a.look, a.seconds))
    if len(uniq) < 2:
        raise SystemExit(f"poucos frames capturados ({len(uniq)}); rode de novo")
    period = one_period(uniq)
    if period:
        n, diff = period
        sel, loop = uniq[:n], a.seconds * n / len(uniq)  # periodo em segundos reais
        # amarra o tamanho do arquivo: no maximo 120 frames por periodo
        if len(sel) > 120:
            k = [min(len(sel) - 1, round(i * (len(sel) - 1) / 119)) for i in range(120)]
            sel = [sel[i] for i in k]
    else:
        sel, loop = uniq, float(a.seconds)
        print(f"aviso: ciclo nao detectado; loop pode dar salto ({len(uniq)} frames)")
    build(sel, out, loop)


if __name__ == "__main__":
    main()
