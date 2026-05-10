"""Graphical rectangle picker (tkinter) for selecting terminal area on a screenshot.

Usage: python -m termshot picker <image> [--output coords.txt]

Opens the image in a window. Click and drag to draw a rectangle.
Press Enter to print coordinates and exit. Press Escape to cancel.
"""

import sys
import os
import json


def pick_rectangle(image_path: str) -> dict | None:
    try:
        import tkinter as tk
        from PIL import Image, ImageTk
    except ImportError as e:
        print(f"Error: {e}. Install: pip install Pillow (tkinter is built-in on Windows/macOS)")
        return None

    if not os.path.isfile(image_path):
        print(f"Error: file not found: {image_path}")
        return None

    img = Image.open(image_path)
    result: dict = {}

    root = tk.Tk()
    root.title(f"term-shot picker — {os.path.basename(image_path)}")
    root.configure(bg='#1a1a2e')

    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    max_w = int(screen_w * 0.85)
    max_h = int(screen_h * 0.75)

    scale = min(max_w / img.width, max_h / img.height, 1.0)
    disp_w = max(int(img.width * scale), 1)
    disp_h = max(int(img.height * scale), 1)

    display_img = img.resize((disp_w, disp_h), Image.LANCZOS) if scale < 1.0 else img.copy()
    tk_img = ImageTk.PhotoImage(display_img)

    canvas = tk.Canvas(root, width=disp_w, height=disp_h, bg='#000',
                       highlightthickness=0, cursor='crosshair')
    canvas.pack(padx=0, pady=0)
    canvas.create_image(0, 0, anchor='nw', image=tk_img)
    canvas._scale = scale

    rect_id = None
    start_x = start_y = 0

    def on_down(event):
        nonlocal start_x, start_y, rect_id
        start_x, start_y = event.x, event.y
        if rect_id:
            canvas.delete(rect_id)
        rect_id = canvas.create_rectangle(
            start_x, start_y, event.x, event.y,
            outline='#e94560', width=3, dash=(6, 3),
            stipple='gray25'
        )

    def on_move(event):
        nonlocal rect_id
        if rect_id:
            canvas.coords(rect_id, start_x, start_y, event.x, event.y)

    def on_up(event):
        nonlocal rect_id
        if not rect_id:
            return
        x1 = min(start_x, event.x)
        y1 = min(start_y, event.y)
        x2 = max(start_x, event.x)
        y2 = max(start_y, event.y)
        w, h = x2 - x1, y2 - y1
        if w < 5 or h < 5:
            canvas.delete(rect_id)
            rect_id = None
            return
        result['x'] = int(x1 / scale)
        result['y'] = int(y1 / scale)
        result['w'] = int(w / scale)
        result['h'] = int(h / scale)

    def on_key(event):
        if event.keysym == 'Return' or event.keysym == 'KP_Enter':
            if rect_id and result:
                print(f"\nRectangle: x={result['x']} y={result['y']} "
                      f"w={result['w']} h={result['h']}")
                print(f"Use: --bg-x {result['x']} --bg-y {result['y']}")
                root.destroy()
            else:
                status.config(text="Draw a rectangle first (click & drag), then press Enter")
        elif event.keysym == 'Escape':
            print("\nCancelled.")
            result.clear()
            root.destroy()

    info = tk.Label(root, text="Click & drag to select terminal area | Enter = confirm | Esc = cancel",
                    bg='#16213e', fg='#a0a0b0', font=('Segoe UI', 9), pady=6, padx=12)
    info.pack(fill='x')

    status = tk.Label(root, text="Draw a rectangle, then press Enter to confirm",
                      bg='#1a1a2e', fg='#4ecca3', font=('Segoe UI', 8), pady=4)
    status.pack(fill='x')

    root.bind('<ButtonPress-1>', on_down)
    root.bind('<B1-Motion>', on_move)
    root.bind('<ButtonRelease-1>', on_up)
    root.bind('<Key>', on_key)
    root.focus_set()

    x = (screen_w - disp_w) // 2
    y = (screen_h - disp_h) // 2
    root.geometry(f'+{x}+{y}')

    root.mainloop()

    return result if result else None


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m termshot picker <image> [--output coords.json]")
        print("\nOpens a GUI to select a rectangle. Press Enter to confirm, Esc to cancel.")
        print("Output: x y width height (for use with --bg-x --bg-y)")
        sys.exit(1)

    image_path = sys.argv[1]
    output_path = None
    if '--output' in sys.argv:
        idx = sys.argv.index('--output')
        if idx + 1 < len(sys.argv):
            output_path = sys.argv[idx + 1]

    result = pick_rectangle(image_path)

    if result and output_path:
        with open(output_path, 'w') as f:
            json.dump(result, f)
        print(f"Saved to {output_path}")

    if not result:
        sys.exit(1)


if __name__ == '__main__':
    main()
