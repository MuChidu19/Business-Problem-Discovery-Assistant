import re as _re


def json_to_text_global(data):
    if data is None:
        return ""
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        for key in ("result", "output", "content", "text", "answer", "response"):
            if key in data and data[key]:
                return json_to_text_global(data[key])
        if "data" in data:
            return json_to_text_global(data["data"])
        for v in data.values():
            if isinstance(v, str) and len(v) > 10:
                return v
        return "\n".join(f"{k}: {json_to_text_global(v)}" for k, v in data.items() if v)
    if isinstance(data, list):
        return "\n".join(json_to_text_global(x) for x in data if x)
    return str(data)


def sanitize_text_global(text: str) -> str:
    if not text:
        return ""
    t = text.strip()
    t = _re.sub(r'^\s*s\s+', '', t)
    t = _re.sub(r'\n\s*s\s+', '\n', t)
    t = _re.sub(r'Q\d+\s*Answer\s*Explanation\s*:', '', t, flags=_re.IGNORECASE)
    t = _re.sub(r'\*\*(.*?)\*\*', r'\1', t)
    t = _re.sub(r'\*(.*?)\*', r'\1', t)
    t = _re.sub(r'`(.*?)`', r'\1', t)
    t = _re.sub(r'#+\s*', '', t)
    t = _re.sub(r'!\[.*?\]\(.*?\)', '', t)
    t = _re.sub(r'\[(.*?)\]\(.*?\)', r'\1', t)
    t = _re.sub(r'\n{3,}', '\n\n', t)
    t = _re.sub(r' {2,}', ' ', t)
    t = _re.sub(r'(?m)^\s*[-*]\s+', '\u2022 ', t)
    t = _re.sub(r'</?[^>]+>', '', t)
    t = _re.sub(r'& Key Takeaway:', 'Key Takeaway:', t)
    return t.strip()


def format_compact_output(text: str, extra_phrases=None,
                          body_line_height: float = 1.30,
                          heading_color: str = "#8b1e1e",
                          subheading_color: str = "#5c1a1a") -> str:
    if not text:
        return "No data available"

    clean = sanitize_text_global(text)
    clean = clean.replace(" - ", " : ")
    clean = _re.sub(r'(?m)^\s*[-*]\s+', '\u2022 ', clean)

    pats = []
    if extra_phrases:
        for phrase in extra_phrases:
            if any(ch in phrase for ch in r".^$*+?{}[]\\|()"):
                pats.append(phrase)
            else:
                pats.append(_re.escape(phrase))

    lines = clean.splitlines()
    n = len(lines)
    i = 0
    blocks = []
    section_heading_style = f"margin:10px 0 4px; font-size:1.05rem; font-weight:700; color:{heading_color};"
    subheading_style = f"margin:6px 0 2px; font-size:1rem; font-weight:600; color:{subheading_color};"
    body_text_style = f"margin:6px 0; line-height:{body_line_height}; font-size:0.98rem;"

    def add(content, kind="text"):
        blocks.append({"type": kind, "content": content})

    def collect(start_idx):
        acc = [lines[start_idx].rstrip()]
        j = start_idx + 1
        while j < n:
            nxt = lines[j]
            if not nxt.strip():
                break
            if _re.match(r'^\s+', nxt) or _re.match(r'^\s*[a-z]', nxt):
                acc.append(nxt.rstrip())
                j += 1
                continue
            if _re.match(r'^\s*(?:\u2022|-|\d+\.)\s+', nxt):
                break
            break
        return acc, j

    while i < n:
        ln = lines[i].rstrip()
        if not ln.strip():
            add('', 'break')
            i += 1
            continue

        if pats:
            hl = ln
            for pat in pats:
                try:
                    hl = _re.sub(pat, lambda m: f"<strong>{m.group(0)}</strong>", hl, flags=_re.IGNORECASE)
                except _re.error:
                    hl = _re.sub(_re.escape(pat), lambda m: f"<strong>{m.group(0)}</strong>", hl, flags=_re.IGNORECASE)
            if hl != ln:
                add(hl)
                i += 1
                continue

        m_sec = _re.match(r'^\s*Section\s+(\d+)\s*:\s*(.+)$', ln, flags=_re.IGNORECASE)
        if m_sec:
            title = f"Section {m_sec.group(1)}: {m_sec.group(2).strip()}"
            add(f"<h4 style=\"{section_heading_style}\">{title}</h4>", 'heading')
            i += 1
            continue

        if _re.search(r'(Step\s*\d+\s*:)', ln, flags=_re.IGNORECASE):
            blk, j = collect(i)
            add(f"<h5 style=\"{subheading_style}\">{'<br>'.join(b.strip() for b in blk)}</h5>", 'subheading')
            i = j
            continue

        m_num_colon = _re.match(r'^\s*(\d+\.\s+[^:]+):\s*(.*)$', ln)
        if m_num_colon:
            heading = m_num_colon.group(1).strip()
            rest = m_num_colon.group(2).strip()
            add(f"<h5 style=\"{subheading_style}\">{heading}</h5>", 'subheading')
            if rest:
                add(rest)
            i += 1
            continue

        m_num = _re.match(r'^\s*(\d+\.\s+.+)$', ln)
        if m_num:
            blk, j = collect(i)
            add(f"<h5 style=\"{subheading_style}\">{'<br>'.join(b.strip() for b in blk)}</h5>", 'subheading')
            i = j
            continue

        m_bh = _re.match(r'^\s*(?:\u2022|\d+\.)\s*([^:]+):\s*(.*)$', ln)
        if m_bh:
            h = m_bh.group(1).strip()
            r = m_bh.group(2).strip()
            add(f"\u2022 <strong>{h}:</strong> {r}" if r else f"\u2022 <strong>{h}:</strong>")
            i += 1
            continue

        m_side = _re.match(r'^\s*([^:]+):\s*(.*)$', ln)
        if m_side and len(m_side.group(1).split()) <= 8:
            l = m_side.group(1).strip()
            r = m_side.group(2).strip()
            add(f"<strong>{l}:</strong> {r}" if r else f"<strong>{l}:</strong>")
            i += 1
            continue

        add(ln)
        i += 1

    final_blocks, tmp = [], []

    def flush():
        nonlocal tmp
        if tmp:
            final_blocks.append({"type": "text", "content": '<br>'.join(tmp)})
            tmp = []

    for b in blocks:
        if b["type"] == 'break':
            flush()
            continue
        if b["type"] in ('heading','subheading'):
            flush()
            final_blocks.append(b)
        else:
            tmp.append(b["content"])

    flush()

    parts = []
    for b in final_blocks:
        if b["type"] in ('heading','subheading'):
            parts.append(b["content"])
        else:
            parts.append(f"<p style='{body_text_style}'>{b['content']}</p>")

    html = "\n".join(parts)
    html = _re.sub(r'(<br>\s*){3,}', '<br><br>', html)
    return f"<div class='agent-display'>{html}</div>"

