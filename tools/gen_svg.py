#!/usr/bin/env python3
"""ascii-magic piece -> SVG animado colorido (frames em <text>, troca via CSS steps).

Uso:
  python3 tools/gen_svg.py rotating-cube --look=lines --out=cube.svg
  python3 tools/gen_svg.py snake-autoplay --out=snake.svg

Ao sobrescrever um SVG ja referenciado no README, suba o ?v=N na referencia
(nova URL = cache novo). Arquivo novo nao precisa.

Captura com --color --truecolor via pipe: o cli so emite cores com TTY ou
com a flag --color, e no modo pty (script) ele congela a animacao. O loop e
fechado no frame com silhueta mais parecida com a inicial (o cubo gira em
dois eixos e o pose exato demora a repetir).
"""
import argparse
import re
import subprocess
import xml.dom.minidom as minidom

ESC = "\x1b"
FS, ADV, LH = 13, 7.8, 15.6
PAD_X, PAD_Y = 20, 16
BG, FG = "#292724", "#e4e4e7"
MAX_FRAMES = 120

BASIC = ["#000000", "#cd0000", "#00cd00", "#cdcd00", "#0000ee", "#cd00cd",
         "#00cdcd", "#e5e5e5", "#7f7f7f", "#ff0000", "#00ff00", "#ffff00",
         "#5c5cff", "#ff00ff", "#00ffff", "#ffffff"]


def palette(n):
    if n < 16:
        return BASIC[n]
    if n < 232:
        n -= 16
        v = (0, 95, 135, 175, 215, 255)
        return "#%02x%02x%02x" % (v[n // 36], v[n // 6 % 6], v[n % 6])
    g = 8 + 10 * (n - 232)
    return "#%02x%02x%02x" % (g, g, g)


def sgr_fg(params):
    fg = None
    p = [int(x) if x else 0 for x in params.split(";")] if params else [0]
    i = 0
    while i < len(p):
        v = p[i]
        if v in (0, 39):
            fg = None
        elif 30 <= v <= 37:
            fg = BASIC[v - 30]
        elif 90 <= v <= 97:
            fg = BASIC[v - 90 + 8]
        elif v == 38 and i + 1 < len(p):
            if p[i + 1] == 2:
                fg = "#%02x%02x%02x" % tuple((p[i + 2:i + 5] + [0, 0, 0])[:3])
                i += 4
            elif p[i + 1] == 5:
                fg = palette(p[i + 2])
                i += 2
        i += 1
    return fg


def parse_frame(s):
    """String ANSI -> linhas de runs [(texto, cor|None)].

    Cada frame e um redesenho completo a partir do cursor home; \\x1b[K so
    limpa o resto da linha (nada foi desenhado depois) e \\x1b[J limpa abaixo,
    entao ambos sao ignorados. \\n separa linhas.
    """
    lines = [[]]
    fg = None
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == ESC:
            m = re.match(ESC + r"\[([0-9;?]*)([a-zA-Z])", s[i:])
            if not m:
                i += 1
                continue
            params, cmd = m.group(1), m.group(2)
            i += m.end()
            if cmd == "m":
                fg = sgr_fg(params)
        else:
            if c == "\n":
                lines.append([])
            elif c != "\r":
                lines[-1].append((c, fg))
            i += 1
    return lines


def merge_runs(line):
    """Junta chars consecutivos de mesma cor; espacos nao precisam de cor."""
    runs = []
    for ch, fg in line:
        if ch == " ":
            fg = None
        if runs and runs[-1][1] == fg:
            runs[-1][0] += ch
        else:
            runs.append([ch, fg])
    while runs and runs[-1][1] is None and set(runs[-1][0]) <= {" "}:
        runs.pop()
    return runs


def capture(piece, look, seconds):
    # --color --truecolor: sem TTY o cli omite cores; flags forcam truecolor
    # (bin/cli.js: color = (out.isTTY || flags.color) && NO_COLOR undefined).
    cmd = ["npx", "--yes", "ascii-magic-art", piece]
    if look:
        cmd.append(f"--look={look}")
    cmd += [f"--seconds={seconds}", "--color", "--truecolor"]
    p = subprocess.run(cmd, capture_output=True, timeout=seconds + 15, check=False)
    return p.stdout.decode("utf-8", "replace")


def frames(raw):
    """-> lista de frames; cada frame = linhas de runs; e as linhas de chars."""
    out = []
    for part in raw.split(ESC + "[H")[1:]:  # parte 0 = preambulo (spinner)
        fr = parse_frame(part)
        while fr and not fr[0]:
            fr.pop(0)
        while fr and not fr[-1]:
            fr.pop()
        if any(runs for runs in fr):
            out.append(fr)
    uniq = []
    for f in out:
        chars = ["".join(t for t, _ in runs) for runs in f]
        if not uniq or uniq[-1][1] != chars:
            uniq.append((f, chars))
    return uniq


def ndiff(a, b):
    R = max(len(a), len(b))
    C = max(max(len(l) for l in f) for f in (a, b))
    return sum(1 for r in range(R) for c in range(C)
               if (a[r][c] if r < len(a) and c < len(a[r]) else " ")
               != (b[r][c] if r < len(b) and c < len(b[r]) else " "))


def one_period(chars_list):
    if len(chars_list) < 16:
        return None
    filled = sum(1 for l in chars_list[0] for ch in l if ch != " ")
    best = min((ndiff(chars_list[0], chars_list[j]), j) for j in range(12, len(chars_list)))
    if best[0] <= 0.25 * filled:
        return best[1], best[0]
    return None


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build(sel, path, loop):
    chars_list = [chars for _, chars in sel]
    rows = max(len(c) for c in chars_list)
    cols = max(max(len(l) for l in c) for c in chars_list)
    W = round(cols * ADV + 2 * PAD_X)
    H = round(rows * LH + 2 * PAD_Y)
    step = loop / len(sel)
    # classes de cor: <tspan class="cN"> encurta cada run colorido
    fill_ids = {}
    texts = []
    for i, (fr, _) in enumerate(sel):
        tsp = []
        for r, runs in enumerate(fr):
            y = round(PAD_Y + FS * 0.85 + r * LH)
            body = ""
            for t, fg in merge_runs(runs):
                if fg:
                    cid = fill_ids.setdefault(fg, f"c{len(fill_ids)}")
                    body += f'<tspan class="{cid}">{esc(t)}</tspan>'
                else:
                    body += f"<tspan>{esc(t)}</tspan>"
            tsp.append(f'<text x="{PAD_X}" y="{y}">{body}</text>')
        texts.append(
            f'<g class="f" style="animation-delay:{round(i * step, 4)}s">{"".join(tsp)}</g>')
    css_fills = " ".join(f".{cid}{{fill:{fg}}}" for fg, cid in fill_ids.items())
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t">
<title id="t">{esc(path)} - ASCII Magic animation</title>
<style>
text{{font:{FS}px Menlo,Consolas,"DejaVu Sans Mono","Liberation Mono",monospace;fill:{FG};white-space:pre}}
{css_fills}
.f{{opacity:0;animation:swap {round(loop, 2)}s steps(1,end) infinite}}
@keyframes swap{{0%{{opacity:1}}{round(100 / len(sel), 2)}%{{opacity:0}}100%{{opacity:0}}}}
@media (prefers-reduced-motion:reduce){{.f{{animation:none}}.f:first-of-type{{opacity:1}}}}
</style>
<rect width="{W}" height="{H}" rx="12" fill="{BG}"/>
{"".join(texts)}
</svg>
'''
    open(path, "w", encoding="utf-8").write(svg)
    n = len(minidom.parse(path).getElementsByTagName("g"))
    assert n == len(sel), f"self-check: {n} g != {len(sel)} frames"
    print(f"{path}: {len(sel)} frames, loop {round(loop, 2)}s, {rows}x{cols} chars, {W}x{H}px")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("piece", help="ex.: rotating-cube (lista: npx ascii-magic-art --list)")
    ap.add_argument("--look", default=None, help="quando a peca tiver looks: lines | dots | block")
    ap.add_argument("--out", default=None, help="arquivo de saida (default: <piece>.svg)")
    ap.add_argument("--seconds", type=int, default=3, help="duracao da captura (default: 3)")
    ap.add_argument("--max-frames", type=int, default=MAX_FRAMES,
                    help="teto de frames no SVG (0 = sem teto; default: 120)")
    a = ap.parse_args()
    out = a.out or f"{a.piece}.svg"
    uniq = frames(capture(a.piece, a.look, a.seconds))
    if len(uniq) < 2:
        raise SystemExit(f"poucos frames capturados ({len(uniq)}); rode de novo")
    period = one_period([c for _, c in uniq])
    if period:
        n, diff = period
        sel, loop = uniq[:n], a.seconds * n / len(uniq)  # periodo em segundos reais
        if a.max_frames and len(sel) > a.max_frames:  # amarra o tamanho do arquivo
            k = [min(len(sel) - 1, round(i * (len(sel) - 1) / (a.max_frames - 1))) for i in range(a.max_frames)]
            sel = [sel[i] for i in k]
    else:
        sel, loop = uniq, float(a.seconds)
        print(f"aviso: ciclo nao detectado; loop pode dar salto ({len(uniq)} frames)")
    build(sel, out, loop)


if __name__ == "__main__":
    main()
