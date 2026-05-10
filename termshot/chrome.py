"""Window chrome — clean macOS, Ubuntu/GNOME, and Windows 11 terminal title bars."""

import os
from PIL import ImageDraw, ImageFont


def _hex(h):
    h = h.lstrip('#')
    if len(h) == 3:
        h = ''.join(c*2 for c in h)
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _font(size, bold=False):
    d = os.path.join(os.path.dirname(__file__), 'fonts')
    s = '-Bold' if bold else ''
    for fn in (f'DejaVuSans{s}.ttf', f'DejaVuSansMono{s}.ttf'):
        p = os.path.join(d, fn)
        if os.path.isfile(p): return ImageFont.truetype(p, size)
    for sp in ['C:/Windows/Fonts/segoeui.ttf', 'C:/Windows/Fonts/consola.ttf',
               '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
        if os.path.isfile(sp):
            try: return ImageFont.truetype(sp, size)
            except: pass
    return ImageFont.load_default()


def chrome_height(theme) -> int:
    c = theme.chrome
    if c in ('macos', 'ubuntu'): return 28
    if c == 'windows': return 30
    return 0


def draw_chrome(draw, width, theme) -> int:
    c = theme.chrome
    if c == 'macos': return _macos(draw, width, theme)
    if c == 'ubuntu': return _ubuntu(draw, width, theme)
    if c == 'windows': return _win11(draw, width, theme)
    if c == 'virtualbox': return _virtualbox(draw, width, theme)
    return 0


def _macos(draw, w, t):
    H = 28
    bg = _hex(t.titlebar_bg)
    draw.rectangle([0, 0, w, H], fill=bg)
    draw.line([0, H-1, w, H-1], fill=(35, 35, 35))

    by, br = 9, 6
    for i, col in enumerate([(237,76,60), (245,189,46), (96,197,68)]):
        cx = 14 + i*20
        draw.ellipse([cx-br, by, cx+br, by+br*2], fill=col)

    f = _font(11)
    title = t.window_title
    if f:
        tx = (w - draw.textlength(title, font=f))/2
        draw.text((tx, 6), title, fill=(185, 185, 185), font=f)
    return H


def _ubuntu(draw, w, t):
    H = 28
    bg = _hex('#2D2D2D')
    draw.rectangle([0, 0, w, H], fill=bg)

    f = _font(11)
    title = t.window_title
    if f:
        tx = (w - draw.textlength(title, font=f))/2
        draw.text((tx, 6), title, fill=(225, 225, 225), font=f)

    cx = w - 16
    draw.ellipse([cx-7, 8, cx+7, 20], fill=(233, 84, 32))
    if f: draw.text((cx-4, 5), '\u00d7', fill=(255, 255, 255), font=f)
    return H


def _win11(draw, w, t):
    H = 40
    bg = _hex('#1C1C1C')
    draw.rectangle([0, 0, w, H], fill=bg)

    term_bg = _hex(t.background)
    tab_w = min(240, w - 180)
    tab_h = 32
    tab_y = H - tab_h
    tab_x = 8

    try:
        draw.rounded_rectangle([tab_x, tab_y, tab_x + tab_w, H + 10], radius=8, fill=term_bg)
    except AttributeError:
        draw.rectangle([tab_x, tab_y, tab_x + tab_w, H], fill=term_bg)
    
    draw.rectangle([tab_x, H - 8, tab_x + tab_w, H], fill=term_bg)

    f = _font(12)
    title = t.window_title
    if f:
        draw.text((tab_x + 12, tab_y + 8), '>\u200e_', fill=(120, 180, 255), font=f)
        draw.text((tab_x + 34, tab_y + 8), title, fill=(235, 235, 235), font=f)
        
        f_small = _font(10)
        if f_small:
            draw.text((tab_x + tab_w - 24, tab_y + 10), '\u2715', fill=(150, 150, 150), font=f_small)

    add_btn_x = tab_x + tab_w + 6
    if f:
        draw.text((add_btn_x + 6, tab_y + 8), '+', fill=(200, 200, 200), font=f)
        draw.text((add_btn_x + 22, tab_y + 6), '\u02C5', fill=(200, 200, 200), font=f)

    btn_w = 46
    x3 = w - btn_w
    x2 = x3 - btn_w
    x1 = x2 - btn_w

    f2 = _font(11)
    if f2:
        draw.text((x1 + 18, 14), '\u2500', fill=(180, 180, 180), font=f2)
        draw.text((x2 + 18, 12), '\u25A1', fill=(180, 180, 180), font=f2)
        draw.text((x3 + 18, 13), '\u2715', fill=(180, 180, 180), font=f2)

    return H


def _virtualbox(draw, w, t):
    """VirtualBox window frame with titlebar and optional VM menu."""
    titlebar_h = 20
    menu_h = t.vm_menu * 18
    total_h = titlebar_h + menu_h
    
    # Title bar background
    bg = _hex(t.titlebar_bg)
    draw.rectangle([0, 0, w, titlebar_h], fill=bg)
    
    # Title bar border
    border_c = _hex(t.border_color)
    draw.line([0, titlebar_h-1, w, titlebar_h-1], fill=border_c, width=1)
    
    # Title text
    f = _font(10, bold=True)
    title = t.window_title
    if f:
        fg = _hex(t.titlebar_fg)
        draw.text((6, 3), title, fill=fg, font=f)
    
    # VM Menu bar (if enabled)
    if t.vm_menu:
        menu_bg = _hex('#F0F0F0')
        draw.rectangle([0, titlebar_h, w, titlebar_h + menu_h], fill=menu_bg)
        
        f_menu = _font(9)
        if f_menu:
            menu_items = ['File', 'Machine', 'View', 'Input', 'Devices', 'Help']
            x_pos = 4
            fg_menu = _hex('#1E1E1E')
            for item in menu_items:
                draw.text((x_pos, titlebar_h + 2), item, fill=fg_menu, font=f_menu)
                x_pos += len(item) * 6 + 12
    
    # Border (if set)
    if t.border_width > 0:
        bw = int(t.border_width)
        for i in range(bw):
            draw.rectangle([i, i, w-i-1, total_h+i-1], outline=border_c)
    
    return total_h
