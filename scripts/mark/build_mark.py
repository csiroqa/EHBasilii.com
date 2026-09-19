#!/usr/bin/env python3
"""Site mark (几何印) asset builder.

Derives every published icon from one master drawing, so the favicon set, the
header logo and the Safari pinned-tab silhouette can never drift apart.

Usage:
    cd site/root && python scripts/mark/build_mark.py                # install the icon set
    cd site/root && python scripts/mark/build_mark.py --stage=proof  # weight candidates sheet
    cd site/root && python scripts/mark/build_mark.py --stage=mask   # silhouette sheet

Design:
  - Master:  scripts/mark/favicon-master.svg — Inkscape A4 page (210×297 mm).
             The mark itself spans a 64.13 mm square centred on (100, 100), so
             ~94 % of the page is empty margin and must be cropped away.
  - Crop:    viewBox "66 66 68 68" → 6 % optical padding, mark fills 94 %.
  - Weights: optical sizing instead of one-size-fits-all. The master hairline
             (0.2646 mm ≈ 0.41 % of the mark) collapses into a grey smear below
             ~64 px, so each target size gets its own stroke weight — and the
             16 px icon drops the inner weave entirely (see TIERS).
  - Tabs:    every tab-capable icon is *transparent* and takes its ink from the
             browser's colour scheme; an opaque plate reads as a sticker against
             the opposite chrome (a near-white 宣纸 tile glares on a dark tab
             bar). Plates only survive where the surface is ours or has none:
             apple-touch (iOS composites on black) and the .ico shell frames
             (Windows taskbar), which use a 拓本 plate — paper lines on 砚石.
  - Raster:  Inkscape CLI renders every size from vector; the multi-size .ico is
             packed by hand from those exact bitmaps.
"""

import argparse, math, os, re, struct, subprocess, sys, tempfile

# ── paths ──────────────────────────────────────────────────────────────
BASE      = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE      = os.path.join(BASE, 'scripts', 'mark')
MASTER    = os.path.join(HERE, 'favicon-master.svg')
STATIC    = os.path.join(BASE, 'static')
IMAGES    = os.path.join(STATIC, 'images')
WORK      = os.path.join(tempfile.gettempdir(), 'ehbasilii-mark')
INKSCAPE  = os.environ.get('INKSCAPE', r'C:\Program Files\Inkscape\bin\inkscape.exe')

# ── geometry ───────────────────────────────────────────────────────────
VIEWBOX   = (66.0, 66.0, 68.0)   # x, y, size — mark spans 67.93–132.07
BOX       = VIEWBOX[2]

# ── palette (mirrors the site's 四时之色) ───────────────────────────────
INK       = '#2d2822'   # 松烟墨 — light scheme line colour
INK_DARK  = '#e3ddd3'   # 烛纸暖黄 — dark scheme line colour
PAPER     = '#faf7f0'   # 宣纸 — opaque plate for surfaces that need one
STONE     = '#1e1d1a'   # 砚石 — ground of the 拓本 plate (shell icons)

# ── feature groups ─────────────────────────────────────────────────────
CIRCLE, DIA_L, DIA_S, GRID, WEAVE = 'circle', 'dia-large', 'dia-small', 'grid', 'weave'
ALL_FEATURES  = {CIRCLE, DIA_L, DIA_S, GRID, WEAVE}   # 全细节：外圆＋四方胜＋五小胜＋九宫栏＋内层编织
CORE_FEATURES = {CIRCLE, DIA_L, DIA_S, GRID}          # 去内层编织
GRID_FEATURES = {CIRCLE, GRID}                        # 仅外圆＋九宫栏（16 px 可用）

# ── shipping tiers ─────────────────────────────────────────────────────
# Each entry: (icon size px, target line width in device px, feature set).
# The line target is what keeps every size optically matched; the feature set is
# what the drawing can still carry at that size (measured, see --stage=proof).
TIERS = {
    16:  (0.95, GRID_FEATURES),   # tab icon: circle + 九宫栏 only
    32:  (1.35, CORE_FEATURES),   # bookmark / taskbar: diamonds readable again
    48:  (1.55, CORE_FEATURES),   # .ico large frame
    180: (1.60, ALL_FEATURES),    # apple-touch: full drawing
}
SVG_FAVICON = (16, 0.99, GRID_FEATURES)    # tab-sized: browsers render SVG at 16–32 px
SVG_LOGO    = (32, 1.13, CORE_FEATURES)    # header logo slot is 32×32 (mobile 26×26)
MASK_STROKE = (3.60, GRID_FEATURES)        # silhouette: 3.6 mm ≈ 0.85 px at 16 px

# Tab icons are transparent in *every* candidate and take their ink from the
# browser's colour scheme — an opaque plate reads as a sticker on the opposite
# chrome (a 宣纸 tile glares on a dark tab bar). Plate-bearing frames are kept
# for surfaces that have no chrome of their own:
#   - apple-touch-icon: iOS composites transparency onto black, so it needs a plate
#   - .ico 48/256 frames: Windows shell / pinned taskbar, where a self-contained
#     拓本 plate (paper lines knocked out of 砚石) stays readable and on-brand
TAB_PNGS = ((16, 0.95, GRID_FEATURES), (32, 1.35, CORE_FEATURES))
ICO_TAB_FRAMES = ((16, 0.95, GRID_FEATURES), (32, 1.35, CORE_FEATURES))
ICO_SHELL_FRAMES = ((48, 1.55, CORE_FEATURES), (256, 1.60, ALL_FEATURES))

# Weight candidates kept for the design record (`--stage=proof`).
CANDIDATES = [
    ('faithful',  0.2646, ALL_FEATURES,  '原稿线宽'),
    ('medium',    1.600,  ALL_FEATURES,  '中粗线'),
    ('bold',      2.600,  ALL_FEATURES,  '粗线，细节全留'),
    ('bold-lite', 2.600,  CORE_FEATURES, '粗线，去内层编织'),
    ('chip',      3.200,  CORE_FEATURES, '16px 专用，去编织'),
    ('chip-min',  3.600,  GRID_FEATURES, '16px 极简，圆＋九宫栏'),
]

NUM = r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'


# ── master parsing ─────────────────────────────────────────────────────
def parse_attrs(text):
    return dict(re.findall(r'([\w:.-]+)\s*=\s*"([^"]*)"', text))


def load_features():
    """Split the master's ink layer into feature-tagged primitives."""
    src = open(MASTER, encoding='utf-8').read()
    body = re.search(r'<g\b[^>]*id="layer1"[^>]*>(.*)</g>', src, re.S).group(1)
    out = []
    for tag, attrs_text in re.findall(r'<(rect|path|circle)\b(.*?)/>', body, re.S):
        a = parse_attrs(attrs_text)
        style = a.get('style', '')
        sw = float(re.search(r'stroke-width:([\d.]+)', style).group(1)) if 'stroke-width:' in style else 0.0
        if tag == 'circle':
            feature = CIRCLE
        elif tag == 'rect':
            feature = DIA_S if float(a['width']) < 14 else DIA_L
        else:
            feature = GRID if a.get('id', '') in (f'path{i}' for i in range(4, 10)) else WEAVE
        out.append(dict(tag=tag, attrs=a, source_width=sw, feature=feature))
    return out


def scaled_stroke(px, target_px):
    """Stroke width (in viewBox mm units) that renders `target_px` device pixels
    on an icon that is `px` pixels wide."""
    return target_px * BOX / px


# ── SVG serialisation ──────────────────────────────────────────────────
def emit_svg(features, stroke, keep, *, ink=INK, dark_ink=None, light_ink=None,
             width=None, label=''):
    """Serialise one variant.

    `ink` is the base line colour — the one a reader that ignores queries will
    see. `dark_ink` / `light_ink` add `prefers-color-scheme` overrides. The two
    shipped SVG favicons are mirrors of one another (each one's base ink is the
    colour of the scheme it is declared for), so the icon ends up correct
    whichever of them a browser settles on *and* whichever layer it honours —
    the `media` query on the `<link>` or the query inside the document.
    """
    x, y, size = VIEWBOX
    css = ['stroke-linecap:round', 'stroke-linejoin:round',
           'fill:none', 'stroke-opacity:1', 'fill-opacity:1',
           f'stroke:{ink}', f'stroke-width:{stroke:.4f}']
    style = f'.ink{{{";".join(css)}}}'
    if dark_ink:
        style += f'\n    @media (prefers-color-scheme:dark){{.ink{{stroke:{dark_ink}}}}}'
    if light_ink:
        style += f'\n    @media (prefers-color-scheme:light){{.ink{{stroke:{light_ink}}}}}'
    dims = f' width="{width}" height="{width}"' if width else ''
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x:g} {y:g} {size:g} {size:g}"{dims}'
        f' role="img" aria-label="{label}">',
        f'  <title>{label}</title>',
        '  <style>',
        f'    {style}',
        '  </style>',
    ]
    for f in features:
        if f['feature'] not in keep:
            continue
        tag, a = f['tag'], f['attrs']
        if tag == 'rect':
            parts.append(f'  <rect class="ink" x="{a["x"]}" y="{a["y"]}" width="{a["width"]}"'
                         f' height="{a["height"]}" transform="{a.get("transform", "")}"/>')
        elif tag == 'circle':
            parts.append(f'  <circle class="ink" cx="{a["cx"]}" cy="{a["cy"]}" r="{a["r"]}"/>')
        else:
            parts.append(f'  <path class="ink" d="{a["d"]}"/>')
    parts.append('</svg>')
    return '\n'.join(parts) + '\n'


# ── Safari pinned-tab silhouette ───────────────────────────────────────
# mask-icon only honours `fill`: strokes are ignored outright, and the colour
# comes from `color` on the <link>. So the drawing is expanded into filled
# outlines (rings and bars) here, all wound the same way so that nonzero
# filling unions the parts instead of XOR-ing their overlaps.
def path_subpaths(d):
    """Absolute points of every subpath — only the m/M/l/L/h/H/v/V/z commands the
    master actually uses are needed."""
    toks = re.findall(r'[MmLlHhVvZz]|' + NUM, d)
    subs, pts, i, cur, cmd = [], [], 0, (0.0, 0.0), None
    while i < len(toks):
        t = toks[i]
        if re.match(r'[A-Za-z]', t):
            cmd = t
            i += 1
            if cmd in 'Zz':
                if pts:
                    subs.append(pts)
                    pts = []
                continue

        def num():
            nonlocal i
            v = float(toks[i])
            i += 1
            return v

        if cmd in 'Mm':
            if pts:
                subs.append(pts)
                pts = []
            px, py = num(), num()
            cur = (px, py) if cmd == 'M' else (cur[0] + px, cur[1] + py)
            pts.append(cur)
            cmd = 'L' if cmd == 'M' else 'l'
        elif cmd in 'Ll':
            px, py = num(), num()
            cur = (px, py) if cmd == 'L' else (cur[0] + px, cur[1] + py)
            pts.append(cur)
        elif cmd in 'Hh':
            px = num()
            cur = (px, cur[1]) if cmd == 'H' else (cur[0] + px, cur[1])
            pts.append(cur)
        elif cmd in 'Vv':
            py = num()
            cur = (cur[0], py) if cmd == 'V' else (cur[0], cur[1] + py)
            pts.append(cur)
        else:
            raise ValueError(f'unsupported path command {cmd!r}')
    if pts:
        subs.append(pts)
    return subs


def rotate_point(p, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c)


def poly_cmd(points):
    d = [f'M {points[0][0]:.4f},{points[0][1]:.4f}']
    d += [f'L {p[0]:.4f},{p[1]:.4f}' for p in points[1:]]
    d.append('Z')
    return ' '.join(d)


def rect_rotation(attrs):
    m = re.search(r'rotate\((' + NUM + r')', attrs.get('transform', ''))
    return float(m.group(1)) if m else None


def ring_rect(a, stroke):
    x, y, w, h = (float(a['x']), float(a['y']), float(a['width']), float(a['height']))
    outer = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    inner = [(x + stroke, y + stroke), (x + w - stroke, y + stroke),
             (x + w - stroke, y + h - stroke), (x + stroke, y + h - stroke)]
    deg = rect_rotation(a)
    if deg is not None:
        outer = [rotate_point(p, deg) for p in outer]
        inner = [rotate_point(p, deg) for p in inner]
    return poly_cmd(outer) + ' ' + poly_cmd(list(reversed(inner)))


def circle_ring(a, stroke):
    cx, cy, r = float(a['cx']), float(a['cy']), float(a['r'])
    r2 = r - stroke

    def annulus(radius, sweep):
        return (f'M {cx - radius:.4f},{cy:.4f} '
                f'A {radius:.4f},{radius:.4f} 0 1 {sweep} {cx + radius:.4f},{cy:.4f} '
                f'A {radius:.4f},{radius:.4f} 0 1 {sweep} {cx - radius:.4f},{cy:.4f} Z')

    return annulus(r, 1) + ' ' + annulus(r2, 0)


def bar_rect(points, stroke):
    """Thick bars along a subpath, grown perpendicular to each segment.

    Butt ends (no length-wise growth) keep the master's lattice lines — which
    stop exactly on the outer circle — from poking through it.
    """
    half = stroke / 2.0
    frags = []
    for p0, p1 in zip(points, points[1:]):
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        length = math.hypot(dx, dy)
        if length < 1e-9:
            continue
        nx, ny = -dy / length * half, dx / length * half
        frags.append(poly_cmd([(p0[0] + nx, p0[1] + ny), (p1[0] + nx, p1[1] + ny),
                               (p1[0] - nx, p1[1] - ny), (p0[0] - nx, p0[1] - ny)]))
    return ' '.join(frags)


def emit_silhouette(features, stroke, keep, label=''):
    x, y, size = VIEWBOX
    frags = []
    for f in features:
        if f['feature'] not in keep:
            continue
        a, tag = f['attrs'], f['tag']
        if tag == 'rect':
            frags.append(ring_rect(a, stroke))
        elif tag == 'circle':
            frags.append(circle_ring(a, stroke))
        else:
            for sp in path_subpaths(a['d']):
                frags.append(bar_rect(sp, stroke))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x:g} {y:g} {size:g} {size:g}"'
            f' role="img" aria-label="{label}">\n'
            f'  <title>{label}</title>\n'
            f'  <path fill="#000000" fill-rule="nonzero" d="{" ".join(frags)}"/>\n'
            '</svg>\n')


# ── raster pipeline ────────────────────────────────────────────────────
def render(svg_path, png_path, px, background=None, opacity=0):
    os.makedirs(os.path.dirname(png_path), exist_ok=True)
    cmd = [INKSCAPE, svg_path, '--export-type=png', f'--export-filename={png_path}',
           f'--export-width={px}', f'--export-height={px}']
    if background:
        cmd += [f'--export-background={background}', f'--export-background-opacity={opacity}']
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return png_path


def render_tier(features, px, target_px, keep, *, bg=None, ink=INK, name=None):
    """Render one icon: `bg=None` keeps it transparent (tab icons), otherwise the
    icon sits on an opaque plate (`bg`, `ink` set the plate's line colour)."""
    stroke = scaled_stroke(px, target_px)
    name = name or f'tier-{px}'
    svg = os.path.join(WORK, f'{name}.svg')
    png = os.path.join(WORK, f'{name}.png')
    open(svg, 'w', encoding='utf-8').write(emit_svg(features, stroke, keep, ink=ink, label=name))
    render(svg, png, px, background=bg, opacity=255 if bg else 0)
    return png, stroke


def pack_ico(sizes, out):
    """Pack vector-rendered bitmaps into one multi-size .ico.

    Frames up to 48 px are written as uncompressed 32-bit DIBs (the classic
    layout every reader understands); a 256 px frame is stored as a PNG block to
    keep the file small, which is the convention Windows has followed since
    Vista.
    """
    from PIL import Image
    blobs = []
    for px, png, compress in sizes:
        if compress:
            im = Image.open(png).convert('RGBA')
            if im.size != (px, px):
                im = im.resize((px, px), Image.LANCZOS)
            if im.getextrema()[3][1] == 255:        # opaque plate → drop the alpha channel
                im = (im.convert('RGB')
                        .quantize(colors=96, method=Image.MEDIANCUT, dither=Image.NONE))
            buf = os.path.join(WORK, f'ico-{px}.png')
            im.save(buf, format='PNG', optimize=True)
            blobs.append((px, open(buf, 'rb').read()))
            continue
        im = Image.open(png).convert('RGBA')
        if im.size != (px, px):
            im = im.resize((px, px), Image.LANCZOS)
        pixels = im.load()
        xor = bytearray()
        for y in range(px - 1, -1, -1):                     # DIB rows are bottom-up
            for x in range(px):
                r, g, b, a = pixels[x, y]
                xor += bytes((b, g, r, a))
        stride = ((px + 31) // 32) * 4                      # 1 bpp AND mask, 4-byte aligned
        and_mask = bytes(stride * px)                       # all-zero: alpha carries the shape
        header = struct.pack('<IiiHHIIiiII', 40, px, px * 2, 1, 32, 0,
                             len(xor) + len(and_mask), 0, 0, 0, 0)
        blobs.append((px, header + bytes(xor) + and_mask))

    directory = struct.pack('<HHH', 0, 1, len(blobs))
    offset = len(directory) + 16 * len(blobs)
    entries, data = b'', b''
    for px, blob in blobs:
        dim = 0 if px >= 256 else px
        entries += struct.pack('<BBBBHHII', dim, dim, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
        data += blob
    with open(out, 'wb') as fh:
        fh.write(directory + entries + data)
    return out


# ── proof sheets ───────────────────────────────────────────────────────
def contact_sheet(rows, path):
    from PIL import Image, ImageDraw
    pad, label_w = 14, 235
    row_h = max(c['img'].height for r in rows for c in r['cells'])
    cols = max(len(r['cells']) for r in rows)
    col_w = max(c['img'].width for r in rows for c in r['cells'])
    sheet = Image.new('RGB', (label_w + cols * (col_w + pad) + pad, pad + len(rows) * (row_h + 26) + pad), '#ffffff')
    draw = ImageDraw.Draw(sheet)
    for ri, row in enumerate(rows):
        top = pad + ri * (row_h + 26)
        draw.text((pad, top + row_h // 2), row['label'], fill='#111111')
        x = label_w
        for cell in row['cells']:
            draw.rectangle([x, top, x + cell['img'].width, top + cell['img'].height], fill=cell['bg'])
            sheet.paste(cell['img'], (x, top), cell['img'])
            draw.text((x, top + row_h + 6), cell['caption'], fill='#555555')
            x += col_w + pad
    sheet.save(path)
    return path


def magnify(png, zoom, bg):
    from PIL import Image
    im = Image.open(png).convert('RGBA')
    big = im.resize((im.width * zoom, im.height * zoom), Image.NEAREST)
    return Image.alpha_composite(Image.new('RGBA', big.size, bg), big)


def stage_proof(features):
    """Weight × size matrix — the measurement behind TIERS."""
    rows = []
    for name, stroke, keep, note in CANDIDATES:
        svg = os.path.join(WORK, f'{name}.svg')
        open(svg, 'w', encoding='utf-8').write(emit_svg(features, stroke, keep, ink=INK, label=name))
        cells = []
        for px, zoom in ((16, 10), (32, 6)):
            png = os.path.join(WORK, f'{name}-{px}.png')
            render(svg, png, px, background=None, opacity=0)   # transparent, as in a tab
            cells.append(dict(img=magnify(png, zoom, '#202124'), bg='#202124', caption=f'{px}px×{zoom} 暗色标签栏'))
            cells.append(dict(img=magnify(png, zoom, '#f2f4f7'), bg='#f2f4f7', caption=f'{px}px×{zoom} 亮色标签栏'))
        rows.append(dict(label=f'{name}\nw={stroke:.4f}mm {note}', cells=cells))
    return contact_sheet(rows, os.path.join(WORK, 'proof.png'))


def stage_mask(features):
    """Silhouette sanity check: does the expanded geometry still read at 16 px?"""
    rows = []
    for name, keep, stroke in (('GRID', GRID_FEATURES, MASK_STROKE[0]),
                               ('CORE', CORE_FEATURES, MASK_STROKE[0]),
                               ('ALL', ALL_FEATURES, MASK_STROKE[0])):
        svg = os.path.join(WORK, f'mask-{name}.svg')
        open(svg, 'w', encoding='utf-8').write(emit_silhouette(features, stroke, keep, name))
        cells = []
        for px, zoom in ((16, 10), (32, 6), (96, 2)):
            png = os.path.join(WORK, f'mask-{name}-{px}.png')
            render(svg, png, px, background='#e8eaed', opacity=255)
            cells.append(dict(img=magnify(png, zoom, '#e8eaed'), bg='#e8eaed', caption=f'{px}px×{zoom}'))
        rows.append(dict(label=f'silhouette {name} w={stroke}mm', cells=cells))
    return contact_sheet(rows, os.path.join(WORK, 'proof-mask.png'))


# ── install ────────────────────────────────────────────────────────────
def stage_install(features):
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(IMAGES, exist_ok=True)
    written = []

    def track(path):
        written.append((os.path.relpath(path, BASE).replace('\\', '/'), os.path.getsize(path)))

    # 1. SVG favicon pair — transparent, sized for a tab. Two mirrored documents
    #    so the scheme can be resolved by `media` on the <link> *or* by the query
    #    inside the file, whichever the engine honours.
    px, target, keep = SVG_FAVICON
    for filename, ink, alt in (('favicon.svg', INK, dict(dark_ink=INK_DARK)),
                               ('favicon-dark.svg', INK_DARK, dict(light_ink=INK))):
        path = os.path.join(STATIC, filename)
        open(path, 'w', encoding='utf-8').write(
            emit_svg(features, scaled_stroke(px, target), keep, ink=ink, **alt,
                     label='EHBasilii Orchestration'))
        track(path)

    # 2. Tab PNGs — transparent, one file per scheme, chosen by `media` on the
    #    <link>. The unsuffixed filenames are the canonical light-scheme art, so
    #    decoders that just fetch /favicon-32x32.png get something sensible.
    for px, target, keep in TAB_PNGS:
        for scheme, ink in (('', INK), ('-dark', INK_DARK)):
            png, _ = render_tier(features, px, target, keep, ink=ink,
                                 name=f'favicon-{px}{scheme}')
            dest = os.path.join(STATIC, f'favicon-{px}x{px}{scheme}.png')
            open(dest, 'wb').write(open(png, 'rb').read())
            track(dest)

    # 3. apple-touch-icon — iOS composites transparency onto black, so this one
    #    keeps an opaque 宣纸 plate; it is a home-screen icon, not a tab surface.
    px, target, keep = 180, *TIERS[180]
    png, _ = render_tier(features, px, target, keep, bg=PAPER, name='apple-touch')
    dest = os.path.join(STATIC, 'apple-touch-icon.png')
    open(dest, 'wb').write(open(png, 'rb').read())
    track(dest)

    # 4. favicon.ico pair — tab frames transparent (never a sticker on either
    #    chrome), shell frames on a 拓本 plate for the Windows taskbar and legacy
    #    readers. A .ico cannot adapt on its own, so it is produced per scheme and
    #    swapped by the same in-page script as the PNGs.
    shell_pngs = []
    for px, target, keep in ICO_SHELL_FRAMES:
        png, _ = render_tier(features, px, target, keep, bg=STONE, ink=PAPER,
                             name=f'ico-shell-{px}')
        shell_pngs.append((px, png, px >= 256))
    for filename, ink in (('favicon.ico', INK), ('favicon-dark.ico', INK_DARK)):
        frames = []
        for px, target, keep in ICO_TAB_FRAMES:
            png, _ = render_tier(features, px, target, keep, ink=ink,
                                 name=f'ico-tab-{px}-{ink.strip("#")}')
            frames.append((px, png, False))
        ico = os.path.join(STATIC, filename)
        pack_ico(frames + shell_pngs, ico)
        track(ico)

    # 5. Header / footer logo — transparent, adaptive, 32×32 slot (26×26 mobile).
    #    Referenced through <img>, where the in-document query is honoured, so one
    #    document is enough here.
    px, target, keep = SVG_LOGO
    path = os.path.join(IMAGES, 'site-mark.svg')
    open(path, 'w', encoding='utf-8').write(
        emit_svg(features, scaled_stroke(px, target), keep, ink=INK, dark_ink=INK_DARK,
                 label='EHBasilii Orchestration 站徽'))
    track(path)

    # 6. Safari pinned tab — solid silhouette; mask-icon ignores strokes.
    stroke, keep = MASK_STROKE
    path = os.path.join(STATIC, 'safari-pinned-tab.svg')
    open(path, 'w', encoding='utf-8').write(
        emit_silhouette(features, stroke, keep, 'EHBasilii Orchestration'))
    track(path)

    return written


def main():
    ap = argparse.ArgumentParser(description='Build the EHBasilii site-mark icon set.')
    ap.add_argument('--stage', choices=['install', 'proof', 'mask'], default='install')
    args = ap.parse_args()

    if args.stage != 'install' and not os.path.exists(INKSCAPE):
        sys.exit(f'Inkscape CLI not found at {INKSCAPE!r}')

    features = load_features()
    counts = {}
    for f in features:
        counts[f['feature']] = counts.get(f['feature'], 0) + 1
    print(f'master: {len(features)} primitives {counts}')

    if args.stage == 'proof':
        print(stage_proof(features))
    elif args.stage == 'mask':
        print(stage_mask(features))
    else:
        for rel, size in stage_install(features):
            print(f'  {rel:34s} {size:>9,} B')


if __name__ == '__main__':
    main()
