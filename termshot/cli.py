#!/usr/bin/env python3
import argparse
import sys
import os

from .theme import list_themes, get_theme, load_theme
from .renderer import generate_png, batch_generate
from .pdf_maker import generate_pdf
from .picker import pick_rectangle


def cmd_png(args):
    if args.batch or os.path.isdir(args.input):
        directory = args.input if os.path.isdir(args.input) else os.path.dirname(args.input) or '.'
        pattern = os.path.basename(args.input) if not os.path.isdir(args.input) else '*.txt'
        batch_generate(
            directory=directory,
            theme=args.theme,
            chrome=args.chrome,
            output_dir=args.output_dir,
            width=args.width,
            pattern=pattern if '*' in pattern or '?' in pattern else '*.txt',
        )
    elif args.input.endswith('.txt') or '*' in args.input or '?' in args.input:
        import glob
        files = glob.glob(args.input)
        if not files:
            print(f'No files match: {args.input}')
            return
        for f in sorted(files):
            out = args.output
            if not out and args.output_dir:
                base = os.path.splitext(os.path.basename(f))[0]
                out = os.path.join(args.output_dir, f'{base}.png')
            result = generate_png(f, out, theme=args.theme, chrome=args.chrome,
                                  title=args.title, width=args.width, scale=args.scale)
            print(f'  {result}')
    else:
        result = generate_png(args.input, args.output, theme=args.theme,
                              chrome=args.chrome, title=args.title, width=args.width,
                              scale=args.scale, background_image=args.background)
        print(f'  {result}')


def cmd_pdf(args):
    result = generate_pdf(args.input, args.output)
    print(f'  {result}')


def cmd_list_themes(args):
    names = list_themes()
    if not names:
        print('No themes found.')
        return
    print('Available themes:')
    for name in names:
        t = load_theme(name)
        bg = t.background if t else '???'
        chrome = t.chrome if t else 'none'
        print(f'  {name:<24s} bg={bg}  chrome={chrome}')


def cmd_show_theme(args):
    try:
        t = get_theme(args.theme)
    except ValueError as e:
        print(f'Error: {e}')
        sys.exit(1)

    print(f'Theme: {t.name}')
    print(f'  Background:  {t.background}')
    print(f'  Cursor:      {t.cursor_color}')
    print(f'  Colors:')
    for key in ('prompt_user', 'prompt_host', 'prompt_path', 'separator',
                'command', 'output', 'error', 'warning', 'success', 'info', 'dim'):
        print(f'    {key:<14s} {t.color(key)}')
    print(f'  Font:        {t.font_family} {t.font_size}pt')
    print(f'  Line height: {t.line_height}')
    print(f'  Prompt type: {t.prompt_type}')
    print(f'  Chrome:      {t.chrome}')
    print(f'  Padding:     t={t.pad_top} b={t.pad_bottom} l={t.pad_left} r={t.pad_right}')
    print(f'  Width max:   {t.width_max}')


def cmd_web(args):
    try:
        from .web.app import launch
    except ImportError as e:
        print(f'Web UI dependencies missing. Install: pip install fastapi uvicorn jinja2')
        print(f'Error: {e}')
        sys.exit(1)
    launch(host=args.host, port=args.port)


def cmd_picker(args):
    result = pick_rectangle(args.image)
    if result:
        print(f'x={result["x"]} y={result["y"]} w={result["w"]} h={result["h"]}')
        print(f'Use: --bg-x {result["x"]} --bg-y {result["y"]}')
    else:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        prog='term-shot',
        description='Generate styled terminal screenshots and PDFs from text captures.',
    )
    sub = parser.add_subparsers(dest='command', help='Command')

    p_png = sub.add_parser('png', help='Generate PNG screenshots from capture files')
    p_png.add_argument('input', help='Input .txt file or directory (with --batch)')
    p_png.add_argument('-o', '--output', help='Output .png path')
    p_png.add_argument('-t', '--theme', default='ubuntu-desktop', help='Theme name')
    p_png.add_argument('-c', '--chrome', help='Window chrome (none, macos, ubuntu, windows, virtualbox)')
    p_png.add_argument('--title', help='Window title')
    p_png.add_argument('-w', '--width', type=int, help='Fixed output width in pixels')
    p_png.add_argument('-s', '--scale', type=int, default=1, help='Scale factor for higher DPI (2=retina)')
    p_png.add_argument('--background', help='Background image to composite behind terminal')
    p_png.add_argument('--batch', action='store_true', help='Process all .txt in directory')
    p_png.add_argument('--output-dir', help='Output directory for batch mode')

    p_pdf = sub.add_parser('pdf', help='Generate PDF from markdown')
    p_pdf.add_argument('input', help='Input .md file')
    p_pdf.add_argument('-o', '--output', help='Output .pdf path')

    sub.add_parser('list-themes', help='List available themes')

    p_show = sub.add_parser('show-theme', help='Show theme details')
    p_show.add_argument('theme', help='Theme name')

    p_web = sub.add_parser('web', help='Launch web UI')
    p_web.add_argument('--host', default='127.0.0.1', help='Host to bind (default: 127.0.0.1)')
    p_web.add_argument('--port', type=int, default=8765, help='Port (default: 8765)')

    p_picker = sub.add_parser('picker', help='GUI rectangle picker for VM screenshot overlay')
    p_picker.add_argument('image', help='Path to screenshot image')
    p_picker.add_argument('-o', '--output', help='Save coordinates to JSON file')

    args = parser.parse_args()

    if args.command == 'png':
        cmd_png(args)
    elif args.command == 'pdf':
        cmd_pdf(args)
    elif args.command == 'list-themes':
        cmd_list_themes(args)
    elif args.command == 'show-theme':
        cmd_show_theme(args)
    elif args.command == 'web':
        cmd_web(args)
    elif args.command == 'picker':
        cmd_picker(args)
    else:
        # Default: launch web UI when double-clicked
        cmd_web(argparse.Namespace(host='127.0.0.1', port=8765))


if __name__ == '__main__':
    main()
