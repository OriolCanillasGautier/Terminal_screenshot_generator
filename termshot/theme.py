import os
import re
from typing import Optional, Dict, Any, List

try:
    import yaml
except ImportError:
    yaml = None

BUILTIN_DIR = os.path.join(os.path.dirname(__file__), 'themes', 'builtin')
USER_DIR = os.path.join(os.path.expanduser('~'), '.term-shot', 'themes')

DEFAULTS = {
    'background': '#300A24',
    'cursor_color': '#FFFFFF',
    'colors': {
        'prompt_user': '#4E9A06',
        'prompt_host': '#4E9A06',
        'prompt_path': '#729FCF',
        'separator': '#BABABA',
        'command': '#EEEEEE',
        'output': '#D3D7CF',
        'error': '#CC0000',
        'warning': '#C4A000',
        'success': '#73D216',
        'info': '#3465A4',
        'dim': '#888888',
    },
    'font': {
        'family': 'DejaVu Sans Mono',
        'size': 13,
        'line_height': 18,
    },
    'prompt': {
        'type': 'bash',
        'pattern': r'^[a-z_][\w-]*@[\w.-]+:[^$]*\$ ',
        'format': '{user}@{host}:{path}$ ',
        'user': 'user',
        'host': 'host',
        'path': '~',
    },
    'window': {
        'chrome': 'none',
        'title': 'Terminal',
        'titlebar_bg': '#323232',
        'titlebar_fg': '#CCCCCC',
        'border_color': '#000000',
        'border_width': 0,
    },
    'padding': {'top': 6, 'bottom': 6, 'left': 10, 'right': 10},
    'width_max': 720,
}

ERROR_KEYWORDS = [
    'error', 'denied', 'refused', 'forbidden', 'unauthorized',
    'fail', 'fatal', 'invalid', 'cannot', "can't", 'no such',
    'not found', 'permission', 'unable', 'abort',
]

WARNING_KEYWORDS = [
    'warning', 'warn', 'deprecated', 'careful', 'notice',
]

SUCCESS_KEYWORDS = [
    'success', 'ok', 'done', 'complete', 'finished',
    'active', 'running', 'enabled', 'passed',
]


def _deep_merge(base: Dict, override: Dict) -> Dict:
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _load_yaml(path: str) -> Optional[Dict]:
    if yaml is None:
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def _scan_themes(directory: str) -> List[str]:
    try:
        return sorted(
            os.path.splitext(f)[0]
            for f in os.listdir(directory)
            if f.endswith('.yaml') or f.endswith('.yml')
        )
    except Exception:
        return []


class Theme:
    __slots__ = ('name', 'cfg', '_prompt_re')

    def __init__(self, name: str, cfg: Dict[str, Any]):
        self.name = name
        self.cfg = cfg
        self._prompt_re = None

    def __repr__(self):
        return f'Theme({self.name!r})'

    @property
    def background(self) -> str:
        return self.cfg.get('background', DEFAULTS['background'])

    @property
    def cursor_color(self) -> str:
        return self.cfg.get('cursor_color', DEFAULTS['cursor_color'])

    def color(self, key: str) -> str:
        return self.cfg.get('colors', {}).get(key, DEFAULTS['colors'].get(key, '#FFFFFF'))

    @property
    def font_family(self) -> str:
        return self.cfg.get('font', {}).get('family', DEFAULTS['font']['family'])

    @property
    def font_size(self) -> int:
        return self.cfg.get('font', {}).get('size', DEFAULTS['font']['size'])

    @property
    def line_height(self) -> int:
        return self.cfg.get('font', {}).get('line_height', DEFAULTS['font']['line_height'])

    @property
    def prompt_type(self) -> str:
        return self.cfg.get('prompt', {}).get('type', 'bash')

    @property
    def prompt_format(self) -> str:
        return self.cfg.get('prompt', {}).get('format', '{user}@{host}:{path}$ ')

    @property
    def prompt_user(self) -> str:
        return self.cfg.get('prompt', {}).get('user', 'user')

    @property
    def prompt_host(self) -> str:
        return self.cfg.get('prompt', {}).get('host', 'host')

    @property
    def prompt_path(self) -> str:
        return self.cfg.get('prompt', {}).get('path', '~')

    def prompt_regex(self) -> re.Pattern:
        if self._prompt_re is None:
            pattern = self.cfg.get('prompt', {}).get('pattern', DEFAULTS['prompt']['pattern'])
            self._prompt_re = re.compile(pattern)
        return self._prompt_re

    @property
    def chrome(self) -> str:
        return self.cfg.get('window', {}).get('chrome', 'none')

    @property
    def window_title(self) -> str:
        return self.cfg.get('window', {}).get('title', 'Terminal')

    @property
    def titlebar_bg(self) -> str:
        return self.cfg.get('window', {}).get('titlebar_bg', '#323232')

    @property
    def titlebar_fg(self) -> str:
        return self.cfg.get('window', {}).get('titlebar_fg', '#CCCCCC')

    @property
    def border_color(self) -> str:
        return self.cfg.get('window', {}).get('border_color', '#000000')

    @property
    def border_width(self) -> int:
        return self.cfg.get('window', {}).get('border_width', 0)

    @property
    def vm_menu(self) -> bool:
        return self.cfg.get('window', {}).get('vm_menu', False)

    @property
    def chrome_style(self) -> str:
        return self.cfg.get('window', {}).get('chrome_style', '')

    def pad(self, side: str) -> int:
        return self.cfg.get('padding', {}).get(side, DEFAULTS['padding'].get(side, 6))

    @property
    def pad_top(self) -> int:
        return self.pad('top')

    @property
    def pad_bottom(self) -> int:
        return self.pad('bottom')

    @property
    def pad_left(self) -> int:
        return self.pad('left')

    @property
    def pad_right(self) -> int:
        return self.pad('right')

    @property
    def width_max(self) -> int:
        return self.cfg.get('width_max', DEFAULTS['width_max'])

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.cfg)


def load_theme(name: str) -> Optional[Theme]:
    for directory in (USER_DIR, BUILTIN_DIR):
        for ext in ('.yaml', '.yml'):
            path = os.path.join(directory, name + ext)
            if os.path.isfile(path):
                data = _load_yaml(path)
                if data:
                    merged = _deep_merge(DEFAULTS, data)
                    return Theme(name, merged)
    return None


def list_themes() -> List[str]:
    themes = set()
    for d in (BUILTIN_DIR, USER_DIR):
        themes.update(_scan_themes(d))
    return sorted(themes)


def get_theme(name: str) -> Theme:
    t = load_theme(name)
    if t is None:
        names = list_themes()
        raise ValueError(
            f"Theme '{name}' not found. Available: {', '.join(names) or '(none)'}"
        )
    return t
