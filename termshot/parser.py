"""Capture file parser with prompt segmentation, output syntax highlighting,
and nano editor detection."""

import re
from typing import List, Tuple, Optional

Token = Tuple[str, str, Optional[List[Tuple[str, str]]]]

IP_PAT = re.compile(
    r'(?<!\d)(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?:/\d{1,2})?)'
    r'|(?<!\w)([0-9a-fA-F]{1,4}(?::[0-9a-fA-F]{1,4}){2,7}(?:/\d{1,3})?)'
    r'|(?<!\w)(::1)(?!\d)'
    r'|(?<!\w)(fe80::[0-9a-fA-F:]+)(?!\w)'
)
IFACE_PAT = re.compile(
    r'\b(lo|eth\d+|enp\w+|wlp\w+|wlan\d+|tun\d+|tap\d+|docker\d+|br-\w+|virbr\d+'
    r'|Ethernet\d+|Wi-Fi\d*)\b'
)
PATH_PAT = re.compile(r'(?<!\w)(/~?[\w./-]{3,}|\w+[\w./-]{2,}\.[\w]{1,4})(?!\w)')

STATUS_GOOD = re.compile(
    r'\b(?:active|running|listening|enabled|UP|OK|ok|success|loaded|passed'
    r'|Installed|installed|configured|started|bound|established|open'
    r'|yes|on|true|available|reachable|Preferred|Running'
    r'|True|Infinite)\b'
)
STATUS_BAD = re.compile(
    r'\b(?:error|Error|fail|fatal|FATAL|invalid|Invalid|cannot|denied|refused|forbidden'
    r'|unauthorized|not found|down|DOWN|dead|stopped|disabled|failed'
    r'|aborted|broken|missing|unavailable|timed out|False|DENIED)\b'
)
STATUS_WARN = re.compile(
    r'\b(?:warning|Warning|warn|deprecated|notice|degraded|inactive|masked'
    r'|limited|partial|stale|Unknown|UNKNOWN)\b'
)
NUMBER_PAT = re.compile(
    r'(?<!\w)(\d{2,}(?:\.\d+)?%?|[0-9]+(?:\.[0-9]+){0,1}\s*(?:KB|MB|GB|TB|ms|s|B|bps|MHz|GHz)?)(?!\w)'
)

NANO_TITLE_RE = re.compile(
    r'^\s*(?:GNU\s+nano|nano)\s+[\d.]+\s+(.+?)(?:\s+(Modified|New\s+Buffer))?\s*$'
)
NANO_BAR_RE = re.compile(
    r'^(\^[A-Z]\s+.+?)(\s{2,})(\^[A-Z]\s+.+?)'
)

ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub('', text)


def _segment_bash_prompt(text: str) -> List[Tuple[str, str]]:
    m = re.match(
        r'^(?P<user>[a-zA-Z_][\w.-]*)@(?P<host>[\w.-]+):(?P<path>[^$#]*)(?P<pchar>[$#])\s*',
        text,
    )
    if not m:
        return [(text, 'command')]

    segments = []
    user = m.group('user')
    host = m.group('host')
    path = m.group('path')
    pchar = m.group('pchar')

    if user:
        segments.append((user, 'prompt_user'))
    segments.append(('@', 'separator'))
    if host:
        segments.append((host, 'prompt_host'))
    segments.append((':', 'separator'))
    if path:
        if path == '~':
            segments.append((path, 'prompt_path'))
        else:
            dirs = path.split('/')
            for i, d in enumerate(dirs):
                if d:
                    segments.append((d, 'prompt_path'))
                if i < len(dirs) - 1 or (path.endswith('/') and i < len(dirs) - 1):
                    segments.append(('/', 'separator'))
    segments.append((pchar, 'separator'))
    return segments


def _segment_ps_prompt(text: str) -> List[Tuple[str, str]]:
    m = re.match(r'^(?P<ps>PS)\s+(?P<path>[^>\r\n]+)>\s*', text)
    if not m:
        return [(text, 'command')]

    segments = [
        ('PS', 'prompt_user'),
        (' ', 'separator'),
        (m.group('path').strip(), 'prompt_path'),
        ('>', 'separator'),
    ]
    return segments


def segment_prompt(text: str, prompt_type: str) -> List[Tuple[str, str]]:
    if prompt_type == 'powershell':
        return _segment_ps_prompt(text)
    return _segment_bash_prompt(text)


def _highlight_line(text: str) -> List[Tuple[str, str]]:
    if not text:
        return [('', 'output')]

    patterns = [
        (IFACE_PAT, 'prompt_user'),
        (IP_PAT, 'info'),
        (PATH_PAT, 'prompt_path'),
        (STATUS_GOOD, 'success'),
        (STATUS_BAD, 'error'),
        (STATUS_WARN, 'warning'),
        (NUMBER_PAT, 'dim'),
    ]

    matches = []
    for pat, color_key in patterns:
        for m in pat.finditer(text):
            matches.append((m.start(), m.end(), color_key))

    matches.sort(key=lambda x: (x[0], -(x[1] - x[0])))

    filtered = []
    last_end = 0
    for start, end, color_key in matches:
        if start >= last_end:
            filtered.append((start, end, color_key))
            last_end = end

    segments = []
    pos = 0
    for start, end, color_key in filtered:
        if pos < start:
            segments.append((text[pos:start], 'output'))
        segments.append((text[start:end], color_key))
        pos = end
    if pos < len(text):
        segments.append((text[pos:], 'output'))

    return segments if segments else [(text, 'output')]


def _detect_nano_lines(lines: List[str], start: int, prompt_re: Optional[re.Pattern] = None) -> Optional[Tuple[int, List[Token]]]:
    if start >= len(lines):
        return None

    title_match = NANO_TITLE_RE.match(lines[start])
    if not title_match:
        return None

    tokens: List[Token] = []
    tokens.append(('nano_title', lines[start], None))

    content_start = start + 1
    bar1_idx = None
    bar2_idx = None

    search_end = min(content_start + 70, len(lines))
    for i in range(content_start, search_end):
        ansi_free = strip_ansi(lines[i].rstrip())
        if prompt_re and prompt_re.match(ansi_free):
            search_end = i
            break
        stripped = ansi_free.strip()
        if stripped.startswith('^G') or stripped.startswith('^X') or stripped.startswith('^O'):
            if bar1_idx is None:
                bar1_idx = i
            elif bar2_idx is None:
                bar2_idx = i
                break

    content_end = bar1_idx if bar1_idx is not None else min(content_start + 40, search_end)

    for i in range(content_start, content_end):
        tokens.append(('nano_content', lines[i].rstrip(), None))

    if bar1_idx is not None:
        tokens.append(('nano_bar1', lines[bar1_idx], None))
    if bar2_idx is not None:
        tokens.append(('nano_bar2', lines[bar2_idx], None))

    end_idx = max(content_end, bar2_idx or 0, bar1_idx or 0)
    if bar2_idx is not None:
        end_idx = bar2_idx + 1
    elif bar1_idx is not None:
        end_idx = bar1_idx + 1

    return end_idx, tokens


_PROMPT_BASH_RE = re.compile(r'^[a-zA-Z_][\w.-]*@[\w.-]+:[^$#]*[$#]\s*')
_PROMPT_PS_RE = re.compile(r'^PS\s+\S+>\s*')


def parse_capture(
    text: str,
    prompt_re: Optional[re.Pattern] = None,
    prompt_type: str = 'bash',
) -> List[Token]:
    tokens: List[Token] = []
    lines = text.rstrip().split('\n')
    i = 0

    if prompt_re is None:
        if prompt_type == 'powershell':
            prompt_re = _PROMPT_PS_RE
        else:
            prompt_re = _PROMPT_BASH_RE

    while i < len(lines):
        line = lines[i].rstrip()
        ansi_free = strip_ansi(line)

        if not ansi_free:
            tokens.append(('output', '', [('', 'output')]))
            i += 1
            continue

        pm = prompt_re.match(ansi_free)
        if pm:
            prompt_text = ansi_free[:pm.end()]
            cmd_text = ansi_free[pm.end():].strip()

            segments = segment_prompt(prompt_text, prompt_type)
            if cmd_text:
                segments.append((' ', 'separator'))
                segments.append((cmd_text, 'command'))

            tokens.append(('prompt_line', ansi_free, segments))
            i += 1
            continue

        nano_result = _detect_nano_lines(lines, i, prompt_re)
        if nano_result:
            end_idx, nano_tokens = nano_result
            tokens.extend(nano_tokens)
            i = end_idx
            continue

        highlighted = _highlight_line(ansi_free)
        if STATUS_BAD.search(ansi_free):
            tokens.append(('error', ansi_free, highlighted))
        elif STATUS_WARN.search(ansi_free):
            tokens.append(('warning', ansi_free, highlighted))
        else:
            tokens.append(('output', ansi_free, highlighted))

        i += 1

    return tokens
