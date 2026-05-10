import os
import re
from html.parser import HTMLParser
from typing import Optional

from fpdf import FPDF, XPos, YPos

def _load_pdf_font(pdf: FPDF, style: str, family: str) -> str:
    fonts_dir = os.path.join(os.path.dirname(__file__), 'fonts')
    name_map = {
        'dejavu sans': ('DejaVuSans.ttf', 'DejaVuSans-Bold.ttf'),
        'dejavu sans mono': ('DejaVuSansMono.ttf', 'DejaVuSansMono-Bold.ttf'),
    }
    key = family.lower().replace('-', ' ')
    if key in name_map:
        regular, bold = name_map[key]
        regular_path = os.path.join(fonts_dir, regular)
        bold_path = os.path.join(fonts_dir, bold)
        font_name = 'CustomBody' if 'sans ' in key else 'CustomMono'
        font_key = (font_name, style)
        
        if not hasattr(pdf, '_loaded_fonts'):
            pdf._loaded_fonts = set()
            
        if font_key not in pdf._loaded_fonts:
            try:
                if style == 'B' and os.path.isfile(bold_path):
                    pdf.add_font(font_name, 'B', bold_path)
                elif os.path.isfile(regular_path):
                    pdf.add_font(font_name, '', regular_path)
                pdf._loaded_fonts.add(font_key)
            except Exception:
                pass
        return font_name

    return 'Helvetica'


def clean_markdown(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    return text


class _PDFHTMLRenderer(HTMLParser):
    def __init__(self, pdf: FPDF, mw: float, body_font: str, mono_font: str):
        super().__init__()
        self.pdf = pdf
        self.mw = mw
        self.body_font = body_font
        self.mono_font = mono_font
        self.stack: list[dict] = []
        self.in_code_block = False
        self.code_lines: list[str] = []
        self.list_counter = 0
        self._buf = ''
        self._skip_data = False

    def _state(self) -> dict:
        return self.stack[-1] if self.stack else {
            'font': self.body_font, 'style': '', 'size': 10,
            'align': 'L', 'tag': None,
        }

    def _push(self, **kw):
        self.stack.append({**self._state(), **kw})

    def _pop(self):
        if self.stack:
            self.stack.pop()

    def _flush_buf(self):
        if not self._buf.strip():
            self._buf = ''
            return
        st = self._state()
        text = self._buf.strip()
        self._buf = ''
        try:
            self.pdf.set_font(st['font'], st.get('style', ''), st.get('size', 10))
        except Exception:
            self.pdf.set_font(self.body_font, '', 10)
        self.pdf.multi_cell(self.mw, st.get('line_h', 5), text, align=st.get('align', 'L'),
                            new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def handle_starttag(self, tag: str, attrs: list):
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self._flush_buf()
            sizes = {1: 20, 2: 16, 3: 13, 4: 11, 5: 10, 6: 9}
            level = int(tag[1])
            self.pdf.ln(4)
            self._push(tag=tag, font=self.body_font, style='B',
                       size=sizes.get(level, 10), line_h=7, align='L')
        elif tag == 'p':
            self._flush_buf()
            self.pdf.ln(1)
            self._push(tag='p', font=self.body_font, size=10, line_h=5, align='L')
        elif tag == 'pre':
            self._flush_buf()
            self.in_code_block = True
            self.code_lines = []
            self._skip_data = False
        elif tag == 'code' and not self.in_code_block:
            pass
        elif tag == 'strong' or tag == 'b':
            st = self._state()
            current = st.get('style', '')
            self._push(style=current + 'B' if 'B' not in current else current)
        elif tag == 'em' or tag == 'i':
            st = self._state()
            current = st.get('style', '')
            self._push(style=current + 'I' if 'I' not in current else current)
        elif tag in ('ul', 'ol'):
            self._flush_buf()
            self.list_counter = 0
            self._push(tag=tag, size=10, line_h=5, align='L', font=self.body_font)
        elif tag == 'li':
            self._flush_buf()
            st = self._state()
            prefix = '  - ' if st.get('tag') == 'ul' else f'  {self.list_counter + 1}. '
            self.list_counter += 1
            self._buf = prefix
        elif tag == 'blockquote':
            self._flush_buf()
            self.pdf.set_fill_color(240, 240, 240)
            self.pdf.set_text_color(80, 80, 80)
            self.pdf.set_font(self.body_font, 'I', 9)
            self._push(tag='blockquote', font=self.body_font, style='I', size=9)
        elif tag == 'hr':
            self._flush_buf()
            self.pdf.ln(2)
            y = self.pdf.get_y()
            self.pdf.set_draw_color(180, 180, 180)
            self.pdf.line(self.pdf.l_margin, y, self.pdf.l_margin + self.mw, y)
            self.pdf.ln(3)
        elif tag == 'img':
            self._flush_buf()
            src = dict(attrs).get('src', '')
            if src and os.path.isfile(src):
                try:
                    self.pdf.ln(1)
                    self.pdf.image(src, x=self.pdf.l_margin, w=self.mw)
                    self.pdf.ln(2)
                except Exception:
                    pass
        elif tag == 'table':
            self._flush_buf()
            self._push(tag='table')
        elif tag == 'thead':
            pass
        elif tag == 'tbody':
            pass

    def handle_endtag(self, tag: str):
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self._flush_buf()
            self._pop()
            self.pdf.ln(4)
        elif tag == 'p':
            self._flush_buf()
            self._pop()
            self.pdf.ln(2)
        elif tag == 'pre':
            if self.code_lines:
                self._render_code_block()
            self.in_code_block = False
            self.code_lines = []
        elif tag == 'code' and not self.in_code_block:
            pass
        elif tag in ('strong', 'b', 'em', 'i'):
            self._pop()
        elif tag in ('ul', 'ol'):
            self._flush_buf()
            self._pop()
            self.pdf.ln(2)
        elif tag == 'li':
            self._flush_buf()
        elif tag == 'blockquote':
            self._flush_buf()
            self._pop()
            self.pdf.set_text_color(0, 0, 0)
            self.pdf.ln(2)
        elif tag == 'table':
            self._pop()

    def handle_data(self, data: str):
        if self.in_code_block:
            self.code_lines.append(data)
            return
        if self._skip_data:
            return
        st = self._state()
        if st.get('tag') in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p',
                             'blockquote', 'li', 'ul', 'ol'):
            self._buf += data

    def _render_code_block(self):
        self.pdf.ln(1)
        self.pdf.set_fill_color(240, 240, 240)
        self.pdf.set_draw_color(200, 200, 200)
        self.pdf.set_font(self.mono_font, '', 8)

        text = ''.join(self.code_lines).rstrip()
        lines = text.split('\n')
        block_h = len(lines) * 4.5 + 6
        start_y = self.pdf.get_y()

        if start_y + block_h > self.pdf.h - self.pdf.b_margin:
            self.pdf.add_page()
            start_y = self.pdf.get_y()

        self.pdf.rect(self.pdf.l_margin, start_y, self.mw, block_h, style='D')
        self.pdf.set_xy(self.pdf.l_margin + 3, start_y + 2)
        for line in lines:
            self.pdf.cell(self.mw - 6, 4.5, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.pdf.set_y(start_y + block_h + 2)
        self.pdf.set_font(self.body_font, '', 10)


def generate_pdf(
    input_path: str,
    output_path: Optional[str] = None,
    body_font_family: str = 'DejaVu Sans',
    mono_font_family: str = 'DejaVu Sans Mono',
) -> str:
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Markdown file not found: {input_path}")

    try:
        import markdown
    except ImportError:
        raise ImportError('pip install markdown')

    with open(input_path, 'r', encoding='utf-8') as f:
        md_text = f.read()

    html = markdown.markdown(md_text, extensions=['extra', 'codehilite', 'toc'])

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=10)

    body_font = _load_pdf_font(pdf, '', body_font_family)
    _load_pdf_font(pdf, 'B', body_font_family)
    mono_font = _load_pdf_font(pdf, '', mono_font_family)

    pdf.add_page()
    mw = pdf.w - pdf.l_margin - pdf.r_margin

    renderer = _PDFHTMLRenderer(pdf, mw, body_font, mono_font)
    renderer.feed(html)
    renderer._flush_buf()

    if output_path is None:
        base = os.path.splitext(os.path.basename(input_path))[0]
        output_path = f'{base}.pdf'

    pdf.output(output_path)
    return f'{output_path}'
