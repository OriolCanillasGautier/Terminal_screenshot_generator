"""PNG renderer with per-segment coloring, nano editor support, and window chrome."""

import os
import glob as _glob
from typing import List, Optional

from PIL import Image, ImageDraw, ImageFont

from .theme import Theme, get_theme
from .parser import parse_capture, Token
from .chrome import draw_chrome, chrome_height


def _hex_to_rgb(h: str):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _find_font(family: str, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    fonts_dir = os.path.join(os.path.dirname(__file__), 'fonts')

    family_lower = family.lower().replace('-', ' ')
    bundle_map = {
        'dejavu sans mono': ('DejaVuSansMono.ttf', 'DejaVuSansMono-Bold.ttf'),
        'dejavu sans': ('DejaVuSans.ttf', 'DejaVuSans-Bold.ttf'),
        'cascadia code': ('CascadiaCode.ttf', 'CascadiaCode.ttf'),
        'consolas': ('consola.ttf', 'consolab.ttf'),
        'ubuntu mono': ('UbuntuMono.ttf', 'UbuntuMono-Bold.ttf'),
    }

    if family_lower in bundle_map:
        regular, bold_file = bundle_map[family_lower]
        target = bold_file if bold else regular
        path = os.path.join(fonts_dir, target)
        if os.path.isfile(path):
            return ImageFont.truetype(path, size)

    path = os.path.join(fonts_dir, 'DejaVuSansMono-Bold.ttf' if bold else 'DejaVuSansMono.ttf')
    if os.path.isfile(path):
        return ImageFont.truetype(path, size)

    system_paths = [
        'C:/Windows/Fonts/consola.ttf',
        'C:/Windows/Fonts/cour.ttf',
        'C:/Windows/Fonts/CascadiaCode.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
        '/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf',
        '/System/Library/Fonts/Menlo.ttc',
    ]
    for sp in system_paths:
        if os.path.isfile(sp):
            try:
                return ImageFont.truetype(sp, size)
            except Exception:
                pass
    try:
        return ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()


def _char_width(font: ImageFont.FreeTypeFont) -> float:
    try:
        bbox = font.getbbox('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789')
        return (bbox[2] - bbox[0]) / 62
    except Exception:
        return 7.8


def _draw_segments(draw, x: float, y: float, segments: List[tuple],
                   theme: Theme, font: ImageFont.FreeTypeFont, bold_font, cw: float):
    cx = x
    for text, color_key in segments:
        if color_key in ('command', 'output', 'error', 'warning', 'success', 'info', 'dim',
                         'prompt_user', 'prompt_host', 'prompt_path', 'separator'):
            fill = theme.color(color_key)
        else:
            fill = theme.color('output')
        draw.text((cx, y), text, fill=fill, font=font)
        cx += len(text) * cw
    return cx


def render_png(
    tokens: List[Token],
    theme: Theme,
    output_path: str,
    *,
    width: Optional[int] = None,
    scale: int = 1,
    background_image: Optional[str] = None,
    bg_offset_x: int = 0,
    bg_offset_y: int = 0,
) -> str:
    s = max(1, scale)
    font_size = int(theme.font_size * s)
    font = _find_font(theme.font_family, font_size)
    bold_font = _find_font(theme.font_family, font_size, bold=True)
    cw = _char_width(font)
    lh = int(theme.line_height * s)
    pl, pr = int(theme.pad_left * s), int(theme.pad_right * s)
    pt, pb = int(theme.pad_top * s), int(theme.pad_bottom * s)

    max_text_w = 0
    for ttype, raw_text, segments in tokens:
        if ttype == 'nano_title':
            tw = len(raw_text) * cw + 40
        elif ttype in ('nano_bar1', 'nano_bar2'):
            tw = len(raw_text) * cw + 20
        elif segments:
            tw = sum(len(s[0]) for s in segments) * cw
        else:
            tw = len(raw_text) * cw
        if tw > max_text_w:
            max_text_w = tw

    max_w = theme.width_max * s if theme.width_max else 9999
    content_w = max(int(max_text_w + pl + pr), 400)
    if width:
        content_w = width * s
    content_w = min(content_w, max_w)

    bw = theme.border_width * s
    ch = chrome_height(theme) * s
    total_h = ch + len(tokens) * lh + pt + pb + bw

    canvas_w = content_w + bw * 2
    canvas_h = total_h

    has_bg = bool(background_image and os.path.isfile(background_image))
    if has_bg:
        bg_img = Image.open(background_image).convert('RGB')
        bg_w, bg_h = bg_img.size
        out_w, out_h = max(bg_w, canvas_w + bg_offset_x), max(bg_h, canvas_h + bg_offset_y)
        im = Image.new('RGB', (out_w, out_h), (30, 30, 30))
        im.paste(bg_img, (0, 0))
        term_im = Image.new('RGB', (canvas_w, canvas_h), _hex_to_rgb(theme.background))
        draw = ImageDraw.Draw(term_im)
    else:
        im = Image.new('RGB', (canvas_w, canvas_h), _hex_to_rgb(theme.background))
        draw = ImageDraw.Draw(im)

    offset = draw_chrome(draw, canvas_w, theme)
    content_x = bw + pl
    content_y = bw + offset + pt

    for ttype, raw_text, segments in tokens:
        x = content_x
        y = content_y

        if ttype == 'prompt_line' and segments:
            _draw_segments(draw, x, y, segments, theme, font, bold_font, cw)
        elif ttype == 'output' and segments:
            _draw_segments(draw, x, y, segments, theme, font, bold_font, cw)
        elif ttype == 'error' and segments:
            _draw_segments(draw, x, y, segments, theme, font, bold_font, cw)
        elif ttype == 'warning' and segments:
            _draw_segments(draw, x, y, segments, theme, font, bold_font, cw)
        elif ttype == 'nano_title':
            _draw_nano_title(draw, x, y, content_w - pl - pr, raw_text, theme, font, bold_font)
        elif ttype == 'nano_content':
            draw.text((x, y), raw_text, fill=theme.color('output'), font=font)
        elif ttype == 'nano_bar1':
            _draw_nano_bar(draw, x, y, content_w - pl - pr, raw_text, theme, font, bold_font, cw)
        elif ttype == 'nano_bar2':
            _draw_nano_bar(draw, x, y, content_w - pl - pr, raw_text, theme, font, bold_font, cw)
        elif segments:
            _draw_segments(draw, x, y, segments, theme, font, bold_font, cw)
        else:
            draw.text((x, y), raw_text, fill=theme.color('output'), font=font)

        content_y += lh

    if has_bg:
        im.paste(term_im, (bg_offset_x, bg_offset_y))

    im.save(output_path, 'PNG')
    return f'{output_path} ({im.width}x{im.height})'


def _draw_nano_title(draw, x, y, max_w, text, theme, font, bold_font):
    bg = _hex_to_rgb(theme.titlebar_bg)
    fg = _hex_to_rgb(theme.titlebar_fg)
    bar_h = theme.line_height
    draw.rectangle([x - 4, y - 1, x + max_w + 4, y + bar_h + 1], fill=bg)
    if bold_font:
        draw.text((x + 4, y + 1), text.strip(), fill=fg, font=bold_font)
    else:
        draw.text((x + 4, y + 1), text.strip(), fill=fg, font=font)


def _draw_nano_bar(draw, x, y, max_w, text, theme, font, bold_font, cw):
    bg = _hex_to_rgb(theme.titlebar_bg)
    fg = (200, 200, 200)
    bar_h = theme.line_height
    draw.rectangle([x - 4, y - 1, x + max_w + 4, y + bar_h + 1], fill=bg)
    parts = text.strip().split('  ')
    cx = x + 4
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part.startswith('^'):
            key = part[:2]
            rest = part[2:]
            if bold_font:
                draw.text((cx, y + 1), key, fill=theme.color('prompt_user'), font=bold_font)
            else:
                draw.text((cx, y + 1), key, fill=theme.color('prompt_user'), font=font)
            cx += len(key) * cw
            draw.text((cx, y + 1), rest, fill=fg, font=font)
            cx += len(rest) * cw + 3 * cw
        else:
            draw.text((cx, y + 1), part, fill=fg, font=font)
            cx += len(part) * cw + 3 * cw


def generate_png(
    input_path: str,
    output_path: Optional[str] = None,
    theme: str = 'ubuntu-desktop',
    chrome: Optional[str] = None,
    title: Optional[str] = None,
    width: Optional[int] = None,
    scale: int = 1,
    background_image: Optional[str] = None,
    bg_offset_x: int = 0,
    bg_offset_y: int = 0,
) -> str:
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Capture file not found: {input_path}")

    with open(input_path, 'r', encoding='utf-8') as f:
        raw = f.read()

    t = get_theme(theme)
    t.cfg = dict(t.cfg)

    if chrome is not None:
        t.cfg.setdefault('window', {})['chrome'] = chrome
    if title is not None:
        t.cfg.setdefault('window', {})['title'] = title

    tokens = parse_capture(raw, t.prompt_regex(), t.prompt_type)
    if not tokens:
        raise ValueError(f"No parseable content in {input_path}")

    if output_path is None:
        base = os.path.splitext(os.path.basename(input_path))[0]
        output_path = f'{base}.png'

    return render_png(tokens, t, output_path, width=width, scale=scale,
                      background_image=background_image,
                      bg_offset_x=bg_offset_x, bg_offset_y=bg_offset_y)


def batch_generate(
    directory: str = '.',
    theme: str = 'ubuntu-desktop',
    chrome: Optional[str] = None,
    output_dir: Optional[str] = None,
    width: Optional[int] = None,
    pattern: str = '*.txt',
) -> List[str]:
    results = []
    files = _glob.glob(os.path.join(directory, pattern))
    if not files:
        print(f'No files matching {pattern} in {directory}')
        return results

    for f in sorted(files):
        out = None
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            base = os.path.splitext(os.path.basename(f))[0]
            out = os.path.join(output_dir, f'{base}.png')
        try:
            result = generate_png(f, out, theme=theme, chrome=chrome, width=width)
            print(f'  {result}')
            results.append(result)
        except Exception as e:
            print(f'  SKIP {f}: {e}')

    return results
