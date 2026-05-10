# term-shot

Generate styled terminal screenshots and PDFs from text captures and markdown.

## Quick start

```bash
pip install Pillow fpdf2 PyYAML markdown fastapi uvicorn jinja2
python -m termshot web
```

Opens a web UI at `http://127.0.0.1:8765` — paste terminal output, pick a theme, generate PNG.

## CLI usage

```bash
# Generate a screenshot
python -m termshot png capture.txt -t ubuntu-desktop -o out.png

# 2x DPI (retina)
python -m termshot png capture.txt -t dracula -s 2

# With window chrome
python -m termshot png capture.txt -c windows --title "Terminal"

# Composite on a VM screenshot
python -m termshot png capture.txt --background vm-screenshot.png --bg-x 120 --bg-y 45

# GUI rectangle picker for VM screenshots
python -m termshot picker vm-screenshot.png

# Batch convert all .txt in a directory
python -m termshot png examples/ --batch --output-dir out/

# Markdown to PDF
python -m termshot pdf document.md -o document.pdf

# List themes
python -m termshot list-themes
```

## Themes (8 built-in)

| Theme | Background | Notes |
|-------|-----------|-------|
| ubuntu-desktop | `#300A24` | Ubuntu GNOME Terminal purple |
| server | `#000000` | Headless server console |
| virtualbox | `#300A24` | VM terminal colors |
| powershell | `#0C0C0C` | Modern Windows Terminal |
| powershell-classic | `#012456` | Classic blue CMD |
| dracula | `#282A36` | Popular dark theme |
| solarized-dark | `#002B36` | Ethan Schoonover's classic |
| gruvbox | `#282828` | Warm retro dark |

Custom themes: place `.yaml` files in `~/.term-shot/themes/`.

## Capture format

Lines starting with `user@host:path$ ` become colored prompts. Everything else is terminal output.
The parser auto-detects IPs, paths, status keywords and applies syntax highlighting.

```
oriol@MV1:~$ ip -br addr show
lo               UNKNOWN        127.0.0.1/8
enp0s3           UP             10.0.2.15/24
```

PowerShell captures:
```
PS C:\Users\oriol> Get-NetIPAddress
IPAddress : 192.168.1.100
```

## Web UI features

- 8 themes with live preview
- Background image upload (VM screenshot compositing)
- Popup rectangle picker for positioning terminal on background
- Window chrome toggle (macOS / Ubuntu / Windows 11)
- Scale slider (1x–4x DPI)
- Copy prompt button
- Markdown → PDF tab

## Project structure

```
term-shot/
├── pyproject.toml
├── termshot/
│   ├── cli.py           # argparse CLI
│   ├── renderer.py      # PNG generation
│   ├── parser.py        # capture parsing + syntax highlighting
│   ├── pdf_maker.py     # markdown → PDF
│   ├── chrome.py        # window chrome renderer
│   ├── theme.py         # theme loader
│   ├── picker.py        # tkinter GUI rectangle picker
│   ├── themes/builtin/  # 8 YAML theme files
│   ├── fonts/           # bundled DejaVu fonts
│   └── web/             # FastAPI web UI
└── portable-kit/        # example captures
```
