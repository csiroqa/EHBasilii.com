#!/usr/bin/env python3
"""Pre‑build font subsetter.

Scans content/*.md for CJK characters, generates per‑page → global WOFF2
subsets, and writes data/fonts.json so Hugo can load page‑specific fonts.

Usage:
    cd site/root && python scripts/subsets.py

Design:
  - Per‑page:  only Source Han Serif SC Regular (CJK body text, ~40–200 KB each)
  - Global:    all 4 CJK weights (Serif R/B + Sans R/B) as fallback
  - Hashing:   MD5 of sorted unique CJK chars → identical char sets share one file
"""

import hashlib, json, os, sys, shutil
from fontTools.ttLib import TTCollection, TTFont
from fontTools.subset import Subsetter, Options

# ── paths ──────────────────────────────────────────────────────────────
BASE       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT    = os.path.join(BASE, 'content')
FONTS      = os.path.join(BASE, 'static', 'fonts')
PAGE_DIR   = os.path.join(FONTS, 'page-subsets')
DATA_DIR   = os.path.join(BASE, 'data')
WF         = r'C:\Windows\Fonts'

# ── helpers ────────────────────────────────────────────────────────────
def is_cjk(ch):
    cp = ord(ch)
    return (
        (0x4E00 <= cp <= 0x9FFF) or
        (0x3400 <= cp <= 0x4DBF) or
        (0xF900 <= cp <= 0xFAFF) or
        (0x3000 <= cp <= 0x303F) or
        (0xFF00 <= cp <= 0xFFEF) or
        (0x3100 <= cp <= 0x312F) or
        ch in '，。、；：？！""''（）【】《》—…·・．′″‹›「」『』〈〉〔〕─　！＠＃＄％＾＆＊＋＝｛｝［］｜＼：；＇，。／＜＞？～'
    )

def extract_cjk(text):
    return sorted(set(ch for ch in text if is_cjk(ch)))

def md5_of(s):
    return hashlib.md5(''.join(s).encode('utf-8')).hexdigest()[:16]

# ── subset font → woff2 ───────────────────────────────────────────────
def subset_ttc(ttc_path, index, chars_text, dst_path):
    """Extract font[index] from TTC, subset to chars_text, save as WOFF2."""
    tc = TTCollection(ttc_path)
    font = tc.fonts[index]
    opts = Options()
    opts.layout_features = ['*']
    opts.drop_tables = ['sbix', 'CBLC', 'EBLC']
    subsetter = Subsetter(options=opts)
    subsetter.populate(text=chars_text)
    subsetter.subset(font)
    font.flavor = 'woff2'
    font.save(dst_path)
    font.close()
    tc.close()

def subset_woff2(src_path, chars_text, dst_path):
    """Load existing WOFF2, subset further, re-save as WOFF2."""
    font = TTFont(src_path)
    opts = Options()
    opts.layout_features = ['*']
    opts.drop_tables = ['sbix', 'CBLC', 'EBLC']
    subsetter = Subsetter(options=opts)
    subsetter.populate(text=chars_text)
    subsetter.subset(font)
    font.flavor = 'woff2'
    font.save(dst_path)
    font.close()

# ══════════════════════════════════════════════════════════════════════
#  STEP 1 — collect CJK chars per content file
# ══════════════════════════════════════════════════════════════════════
page_chars = {}        # content_path → list of unique CJK chars
all_chars = set()
nav_chars = set('首页归档分类标签搜索切换主题选择语言日本語中文EnglishfrançaisLatīnumἙλλάς由强力驱动主题修改版本书香发布于收录于阅读全文')

for root, dirs, files in os.walk(CONTENT):
    for fn in files:
        if not fn.endswith('.md'):
            continue
        fpath = os.path.join(root, fn)
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
        chars = extract_cjk(text)
        if not chars:
            continue
        rel = os.path.relpath(fpath, CONTENT).replace('\\', '/')
        page_chars[rel] = chars
        all_chars.update(chars)

# Merge nav chars (shared across all pages)
all_chars.update(extract_cjk('首页归档分类标签搜索切换主题选择语言日本語中文EnglishfrançaisLatīnumἙλλάς由强力驱动主题修改版本书香发布于收录于阅读全文'))

# Separate: per‑page chars = page chars ONLY (no nav overlap)
# The per‑page font only needs to cover article-specific characters.
# Common nav characters stay in the global font.
nav_set = extract_cjk('首页归档分类标签搜索切换主题选择语言日本語中文EnglishfrançaisLatīnumἙλλάς由强力驱动主题修改版本书香发布于收录于阅读全文')

all_text = ''.join(sorted(all_chars))
nav_text = ''.join(nav_set)

print(f'  Total CJK chars:     {len(all_chars)}')
print(f'  Navigation chars:    {len(nav_set)}')
print(f'  Content files:       {len(page_chars)}')

# ══════════════════════════════════════════════════════════════════════
#  STEP 2 — generate per‑page subsets (Source Han Serif SC Regular only)
# ══════════════════════════════════════════════════════════════════════
os.makedirs(PAGE_DIR, exist_ok=True)

page_font_map = {}               # content_path → md5_hash
page_to_md5 = {}                 # content_path → md5
generated = set()                # md5s already generated (dedup)

ttc_serif_reg = os.path.join(WF, 'SourceHanSerif-Regular.ttc')

for rel, chars in page_chars.items():
    # Only chars unique to this page (nav chars come from global)
    page_only = [c for c in chars if c not in nav_set]
    if not page_only:
        continue

    chars_text = ''.join(page_only)
    h = md5_of(chars_text)
    page_font_map[rel] = h
    page_to_md5[rel] = h

    if h in generated:
        continue
    generated.add(h)

    dst = os.path.join(PAGE_DIR, f'{h}.woff2')
    if os.path.exists(dst):
        continue

    subset_ttc(ttc_serif_reg, 2, chars_text, dst)
    sz = os.path.getsize(dst)
    print(f'  Page font [{h}]: {sz/1024:.0f} KiB  ({rel})')

print(f'  Per‑page fonts: {len(generated)} unique')

# ══════════════════════════════════════════════════════════════════════
#  STEP 3 — generate global fallback (all 4 CJK weights)
# ══════════════════════════════════════════════════════════════════════
# These replace the existing full‑site subset files.
cjk_global = {
    'source-han-serif-sc/SourceHanSerifSC-Regular.woff2': ('SourceHanSerif-Regular.ttc', 2),
    'source-han-serif-sc/SourceHanSerifSC-Bold.woff2':    ('SourceHanSerif-Bold.ttc', 2),
    'source-han-sans-sc/SourceHanSansSC-Regular.woff2':   ('SourceHanSans-Regular.ttc', 2),
    'source-han-sans-sc/SourceHanSansSC-Bold.woff2':      ('SourceHanSans-Bold.ttc', 2),
}

for rel, (ttc_name, idx) in cjk_global.items():
    dst = os.path.join(FONTS, rel)
    print(f'  Global: {rel} …', end=' ')
    subset_ttc(os.path.join(WF, ttc_name), idx, all_text, dst)
    sz = os.path.getsize(dst)
    print(f'{sz/1024:.0f} KiB')

# ══════════════════════════════════════════════════════════════════════
#  STEP 4 — write data/fonts.json
# ══════════════════════════════════════════════════════════════════════
os.makedirs(DATA_DIR, exist_ok=True)
with open(os.path.join(DATA_DIR, 'fonts.json'), 'w', encoding='utf-8') as f:
    json.dump(page_font_map, f, ensure_ascii=False, indent=2)
print(f'  data/fonts.json: {len(page_font_map)} entries')

print('\n✓ Done — fonts subsetted, run `hugo` to build.')
