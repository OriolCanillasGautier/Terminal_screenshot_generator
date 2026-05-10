#!/usr/bin/env python3
"""FastAPI web UI for term-shot."""

import os, io, tempfile, uuid

from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import HTMLResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Template
from PIL import Image

from ..theme import list_themes, get_theme, load_theme
from ..renderer import render_png
from ..parser import parse_capture
from ..pdf_maker import generate_pdf as make_pdf

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates')
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), 'term-shot-uploads')


def read_template(name: str) -> str:
    with open(os.path.join(TEMPLATES_DIR, name), 'r', encoding='utf-8') as f:
        return f.read()


def create_app() -> FastAPI:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    # Clear stale uploads from previous sessions
    for f in os.listdir(UPLOAD_DIR):
        try: os.unlink(os.path.join(UPLOAD_DIR, f))
        except: pass
    app = FastAPI(title='Term-Shot', version='1.0.0')

    if os.path.isdir(STATIC_DIR):
        app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')

    @app.get('/', response_class=HTMLResponse)
    async def index():
        themes = []
        for name in list_themes():
            t = load_theme(name)
            if t:
                themes.append({
                    'id': name, 'name': t.name,
                    'background': t.background, 'chrome': t.chrome,
                })
        html = read_template('index.html')
        return HTMLResponse(content=Template(html).render(themes=themes))

    @app.get('/api/themes')
    async def api_themes():
        return [{
            'id': name, 'name': load_theme(name).name,
            'background': load_theme(name).background,
        } for name in list_themes() if load_theme(name)]

    @app.post('/api/generate')
    async def api_generate(
        text: str = Form(...),
        theme: str = Form('ubuntu-desktop'),
        chrome: str = Form(''),
        title: str = Form(''),
        scale: float = Form(1.0),
        bg_x: int = Form(0),
        bg_y: int = Form(0),
        rect_w: int = Form(0),
        rect_h: int = Form(0),
        nano: bool = Form(False),
    ):
        try:
            t = get_theme(theme)
        except ValueError as e:
            return JSONResponse(content={'error': str(e)}, status_code=400)

        if chrome:
            t.cfg.setdefault('window', {})['chrome'] = chrome
        if title:
            t.cfg.setdefault('window', {})['title'] = title

        if nano:
            fname = title if title else "New Buffer"
            text = f"  GNU nano 8.4                      {fname}\n{text}\n\n^G Help          ^O Write Out     ^F Where Is      ^K Cut           \n^X Exit          ^R Read File     ^\\ Replace       ^U Paste         \n"

        tokens = parse_capture(text, t.prompt_regex(), t.prompt_type)
        if not tokens:
            return JSONResponse(content={'error': 'No parseable content'}, status_code=400)

        has_rect = rect_w > 0 and rect_h > 0
        bg_path = None
        if has_rect:
            try:
                candidates = sorted(
                    [f for f in os.listdir(UPLOAD_DIR) if f.endswith(('.png','.jpg','.jpeg'))],
                    key=lambda f: os.path.getmtime(os.path.join(UPLOAD_DIR, f)), reverse=True)
                if candidates:
                    bg_path = os.path.join(UPLOAD_DIR, candidates[0])
            except Exception:
                pass

        tmp = os.path.join(tempfile.gettempdir(), f'ts-{uuid.uuid4().hex}.png')
        sc = max(0.5, min(float(scale), 4.0))
        try:
            if bg_path and has_rect:
                render_png(tokens, t, tmp, width=None, scale=sc)
            else:
                render_png(tokens, t, tmp, width=None, scale=sc,
                           background_image=bg_path, bg_offset_x=bg_x, bg_offset_y=bg_y)
        except Exception as e:
            return JSONResponse(content={'error': str(e)}, status_code=500)

        try:
            term_img = Image.open(tmp).convert('RGBA')
        except Exception:
            try: os.unlink(tmp)
            except: pass
            return JSONResponse(content={'error': 'Render failed'}, status_code=500)

        if bg_path and rect_w > 0 and rect_h > 0:
            try:
                bg_img = Image.open(bg_path).convert('RGBA')
                tw = rect_w
                th = int(term_img.height * (rect_w / term_img.width))
                term_scaled = term_img.resize((tw, th), Image.LANCZOS)
                out = Image.new('RGBA', (bg_img.width, bg_img.height), (30, 30, 30, 0))
                out.paste(bg_img, (0, 0))
                out.paste(term_scaled, (bg_x, bg_y), term_scaled)
                final = out.convert('RGB')
                final.save(tmp, 'PNG')
            except Exception as e:
                pass

        try:
            with open(tmp, 'rb') as f:
                data = f.read()
        finally:
            try: os.unlink(tmp)
            except: pass

        return Response(content=data, media_type='image/png',
                        headers={'Content-Length': str(len(data)), 'Cache-Control': 'no-cache'})

    @app.post('/api/upload-bg')
    async def api_upload_bg(file: UploadFile = File(...)):
        if not file.filename:
            return JSONResponse(content={'error': 'No file'}, status_code=400)
        name = f'bg-{uuid.uuid4().hex}.png'
        path = os.path.join(UPLOAD_DIR, name)
        content = await file.read()
        try:
            img = Image.open(io.BytesIO(content)).convert('RGB')
            img.save(path, 'PNG')
        except Exception as e:
            return JSONResponse(content={'error': f'Invalid image: {e}'}, status_code=400)
        for old in os.listdir(UPLOAD_DIR):
            if old != name:
                try: os.unlink(os.path.join(UPLOAD_DIR, old))
                except: pass
        return {'ok': True, 'width': img.width, 'height': img.height}

    @app.post('/api/pdf')
    async def api_pdf(markdown: str = Form(...)):
        mp = os.path.join(tempfile.gettempdir(), f'ts-md-{uuid.uuid4().hex}.md')
        with open(mp, 'w', encoding='utf-8') as f: f.write(markdown)
        try:
            pp = os.path.join(tempfile.gettempdir(), f'ts-pdf-{uuid.uuid4().hex}.pdf')
            make_pdf(mp, pp)
            with open(pp, 'rb') as f: data = f.read()
            try: os.unlink(pp)
            except: pass
            return Response(content=data, media_type='application/pdf',
                            headers={'Content-Length': str(len(data))})
        except Exception as e:
            return JSONResponse(content={'error': str(e)}, status_code=500)
        finally:
            try: os.unlink(mp)
            except: pass

    @app.post('/api/batch-script')
    async def api_batch_script(request: Request):
        form = await request.form()
        file = form.get('file')
        code_input = form.get('code')

        if file and getattr(file, 'filename', ''):
            if not file.filename.endswith('.py'):
                return JSONResponse(content={'error': 'Only .py scripts are allowed'}, status_code=400)
            code_str = (await file.read()).decode('utf-8')
        elif code_input:
            code_str = code_input
        else:
            return JSONResponse(content={'error': 'No script provided'}, status_code=400)
            
        ns = {}
        try:
            exec(code_str, {}, ns)
        except Exception as e:
            return JSONResponse(content={'error': f'Failed to parse script: {e}'}, status_code=400)
            
        files_dict = ns.get('files', {})
        md_content = ns.get('md_content', '')
        theme_name = ns.get('theme', 'ubuntu-desktop')
        
        try:
            t = get_theme(theme_name)
        except ValueError:
            t = get_theme('ubuntu-desktop')
            
        from ..parser import _PROMPT_BASH_RE
        
        temp_dir = tempfile.mkdtemp()
        for fname, text in files_dict.items():
            prompt_re = _PROMPT_BASH_RE if ':~$' in text or ':~#' in text else t.prompt_regex()
            ptype = 'bash' if ':~$' in text or ':~#' in text else t.prompt_type
            
            tokens = parse_capture(text, prompt_re, ptype)
            if not tokens: continue
            
            out_path = os.path.join(temp_dir, fname)
            try:
                render_png(tokens, t, out_path, scale=1)
                # Replace exact filename with absolute path in markdown
                md_content = md_content.replace(f"({fname})", f"({out_path.replace(chr(92), '/')})")
            except Exception:
                pass
            
        md_path = os.path.join(temp_dir, 'document.md')
        pdf_path = os.path.join(temp_dir, 'document.pdf')
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
            
        try:
            make_pdf(md_path, pdf_path)
            with open(pdf_path, 'rb') as f:
                data = f.read()
            return Response(content=data, media_type='application/pdf',
                            headers={'Content-Length': str(len(data)), 'Content-Disposition': 'attachment; filename="batch_report.pdf"'})
        except Exception as e:
            return JSONResponse(content={'error': str(e)}, status_code=500)

    return app


def launch(host='127.0.0.1', port=8765):
    import uvicorn, webbrowser
    app = create_app()
    url = f'http://{host}:{port}'
    print(f'\n  Term-Shot Web UI: {url}\n')
    webbrowser.open(url)
    uvicorn.run(app, host=host, port=port, log_level='info')


if __name__ == '__main__':
    launch()
