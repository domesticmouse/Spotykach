#!/usr/bin/env python3
"""Static site builder and validator for the Spotykach Firmware Course."""

from __future__ import annotations

import argparse
import html
import re
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml
from markdown_it import MarkdownIt

ROOT_DIR = Path(__file__).resolve().parent


def create_md() -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": True, "typographer": False})
    md.enable("table")
    return md


MD = create_md()


def parse_frontmatter(raw: str, path: Path) -> tuple[dict[str, Any], str]:
    if not raw.startswith("---\n"):
        raise ValueError(f"{path}: Missing YAML frontmatter block")
    end_idx = raw.find("\n---\n", 4)
    if end_idx == -1:
        raise ValueError(f"{path}: Unclosed YAML frontmatter block")
    fm_text = raw[4:end_idx]
    body = raw[end_idx + 5 :]
    meta = yaml.safe_load(fm_text) or {}
    return meta, body


def render_inline_md(text: str) -> str:
    return MD.renderInline(text.strip())


def rewrite_md_links(text: str) -> str:
    def _repl(match: re.Match[str]) -> str:
        prefix, target, suffix = match.group(1), match.group(2), match.group(3)
        if target.startswith(("http://", "https://", "mailto:", "#")):
            return match.group(0)
        parts = target.split("#", 1)
        path_part = parts[0]
        frag = f"#{parts[1]}" if len(parts) > 1 else ""
        if path_part.endswith("GLOSSARY.md"):
            path_part = path_part[: -len("GLOSSARY.md")] + "glossary.html"
        elif path_part.endswith(".md"):
            path_part = path_part[:-3] + ".html"
        return f"{prefix}{path_part}{frag}{suffix}"

    return re.sub(r"(\]\()([^)\s]+)(\))", _repl, text)


def convert_blank_tokens(code_escaped: str, ex_id: str) -> str:
    counter = 0

    def _repl(match: re.Match[str]) -> str:
        nonlocal counter
        counter += 1
        inner = html.unescape(match.group(1))
        parts = inner.split("|")
        # Support '||' inside answer by recombining before error_hint
        raw_parts = inner.replace("||", "\x00").split("|")
        answer = (raw_parts[0] if len(raw_parts) > 0 else "").replace("\x00", "||")
        error_hint = raw_parts[1] if len(raw_parts) > 1 else "Check syntax and types."
        placeholder = raw_parts[2] if len(raw_parts) > 2 else "..."
        width_ch = raw_parts[3] if len(raw_parts) > 3 else str(max(len(placeholder) + 2, 10))
        try:
            w_num = int(width_ch)
        except ValueError:
            w_num = 12
        blank_id = f"{ex_id}-blank-{counter}"
        return (
            f'<input type="text" id="{html.escape(blank_id)}" '
            f'class="code-blank" '
            f'aria-label="Code blank {counter} for {html.escape(ex_id)}" '
            f'data-answers="{html.escape(answer, quote=True)}" '
            f'data-error-hint="{html.escape(error_hint, quote=True)}" '
            f'placeholder="{html.escape(placeholder, quote=True)}" '
            f'style="width:{w_num}ch;" autocomplete="off" spellcheck="false" />'
        )

    return re.sub(r"\{\{blank:([^}]+)\}\}", _repl, code_escaped)


def render_code_figure(
    lang_info: str, code_body: str, ex_id_for_blanks: str | None = None
) -> str:
    lang_info = lang_info.strip()
    lang_match = re.match(r"^([a-zA-Z0-9_+-]*)(.*)$", lang_info)
    lang = (lang_match.group(1) if lang_match else "") or "text"
    rest = (lang_match.group(2) if lang_match else "").strip()
    cap_match = re.search(r'caption="([^"]+)"', rest)
    caption = cap_match.group(1) if cap_match else None

    if lang == "mermaid":
        cap_html = (
            f"<figcaption>{render_inline_md(caption)}</figcaption>" if caption else ""
        )
        return (
            f'<figure class="mermaid-figure">'
            f'<pre class="mermaid">{html.escape(code_body.strip())}</pre>'
            f"{cap_html}</figure>"
        )

    escaped = html.escape(code_body.rstrip("\n"))
    if ex_id_for_blanks:
        escaped = convert_blank_tokens(escaped, ex_id_for_blanks)

    cap_div = (
        f'<div class="code-caption">{render_inline_md(caption)}</div>'
        if caption
        else ""
    )
    return (
        f'<div class="code-figure">'
        f"{cap_div}"
        f'<pre><code class="language-{html.escape(lang)}">{escaped}</code></pre>'
        f"</div>"
    )


def parse_attrs(attr_str: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for m in re.finditer(r'([a-zA-Z0-9_-]+)="([^"]*)"', attr_str):
        attrs[m.group(1)] = m.group(2)
    return attrs


def render_markdown_fragment(
    text: str,
    placeholders: list[str],
    widget_resolver: Any,
    ex_id_for_blanks: str | None = None,
) -> str:
    # 1. Extract fenced code blocks FIRST before md.render(), link rewrites, or sidenotes
    def _extract_fence(match: re.Match[str]) -> str:
        lang_info = match.group(1)
        code_body = match.group(2)
        rendered = render_code_figure(lang_info, code_body, ex_id_for_blanks)
        idx = len(placeholders)
        placeholders.append(rendered)
        return f"<!--FENCED_CODE_PLACEHOLDER_{idx}-->"

    fence_re = re.compile(r"^```([^\n]*)\n(.*?)^```[ \t]*$", re.MULTILINE | re.DOTALL)
    text = fence_re.sub(_extract_fence, text)

    # 2. Extract widgets
    def _extract_widget(match: re.Match[str]) -> str:
        w_id = match.group(1).strip()
        rendered = widget_resolver(w_id)
        idx = len(placeholders)
        placeholders.append(rendered)
        return f"\n\n<!--FENCED_CODE_PLACEHOLDER_{idx}-->\n\n"

    text = re.sub(r"\{\{widget:([a-zA-Z0-9_-]+)\}\}", _extract_widget, text)

    # 3. Rewrite .md links to .html
    text = rewrite_md_links(text)

    # 4. Convert Tufte sidenotes {{sidenote:...}}
    def _sidenote_repl(match: re.Match[str]) -> str:
        note_md = match.group(1).strip()
        note_html = render_inline_md(note_md)
        idx = len(placeholders)
        placeholders.append(
            f'<span class="sidenote-number"></span>'
            f'<span class="sidenote">{note_html}</span>'
        )
        return f"<!--FENCED_CODE_PLACEHOLDER_{idx}-->"

    text = re.sub(r"\{\{sidenote:(.*?)\}\}", _sidenote_repl, text, flags=re.DOTALL)

    # 5. Convert Table: captions preceding pipe tables
    table_captions: list[str] = []

    def _table_cap_repl(match: re.Match[str]) -> str:
        cap_idx = len(table_captions)
        table_captions.append(render_inline_md(match.group(1).strip()))
        return f"<!--TABLE_CAPTION_{cap_idx}-->\n"

    text = re.sub(
        r"^Table:\s*(.+?)\n(?=\n?\|)",
        _table_cap_repl,
        text,
        flags=re.MULTILINE,
    )

    # 6. Render Markdown via markdown-it
    html_out = MD.render(text)

    # 7. Support heading anchor suffixes {#id}
    def _heading_id_repl(match: re.Match[str]) -> str:
        tag, inner, anchor_id = match.group(1), match.group(2), match.group(3)
        return f'<{tag} id="{html.escape(anchor_id)}">{inner.rstrip()}</{tag}>'

    html_out = re.sub(
        r"<(h[1-6])>(.*?)\s*\{#([a-zA-Z0-9_-]+)\}\s*</\1>",
        _heading_id_repl,
        html_out,
        flags=re.DOTALL,
    )

    # 8. Style GFM tables with .ref-table and scope="col"
    html_out = re.sub(r"<th>", '<th scope="col">', html_out)

    def _inject_table_caption(match: re.Match[str]) -> str:
        cap_idx = int(match.group(1))
        cap_html = table_captions[cap_idx]
        return (
            f'<div class="table-wrap"><table class="ref-table">'
            f"<caption>{cap_html}</caption>"
        )

    html_out = re.sub(
        r"<p><!--TABLE_CAPTION_(\d+)--></p>\s*<table>",
        _inject_table_caption,
        html_out,
    )
    html_out = re.sub(
        r"<!--TABLE_CAPTION_(\d+)-->\s*<table>",
        _inject_table_caption,
        html_out,
    )
    html_out = html_out.replace("<table>", '<div class="table-wrap"><table class="ref-table">')
    html_out = html_out.replace("</table>", "</table></div>")

    return html_out


def render_exercise_block(
    attr_str: str,
    inner: str,
    placeholders: list[str],
    widget_resolver: Any,
) -> str:
    attrs = parse_attrs(attr_str)
    ex_id = attrs.get("id", "ex-0001")
    title = attrs.get("title", "Interactive Lab")
    badge = attrs.get("badge", "Skill Practice")

    prompts_data: dict[str, str] = {}
    prompts_match = re.search(
        r"^:::prompts\s*\n(.*?)^:::[ \t]*$",
        inner,
        flags=re.MULTILINE | re.DOTALL,
    )
    if prompts_match:
        prompts_data = yaml.safe_load(prompts_match.group(1)) or {}
        inner = inner[: prompts_match.start()] + inner[prompts_match.end() :]

    hint_text = str(prompts_data.get("hint", "Review the code blocks above."))
    success_text = str(prompts_data.get("success", "All blanks completed accurately!"))

    body_html = render_markdown_fragment(
        inner, placeholders, widget_resolver, ex_id_for_blanks=ex_id
    )

    return (
        f'<section class="lab-panel exercise-panel" id="{html.escape(ex_id)}" '
        f'aria-labelledby="{html.escape(ex_id)}-title" '
        f'data-hint="{html.escape(hint_text, quote=True)}" '
        f'data-success="{html.escape(success_text, quote=True)}">'
        f'<div class="lab-header">'
        f'<h3 id="{html.escape(ex_id)}-title">{html.escape(title)}</h3>'
        f'<span class="lab-badge">{html.escape(badge)}</span>'
        f"</div>"
        f'<div class="lab-body">'
        f"{body_html}"
        f'<div class="lab-actions">'
        f'<button type="button" class="btn btn-primary" data-action="check">Check Answers</button>'
        f'<button type="button" class="btn" data-action="hint">Hint</button>'
        f'<button type="button" class="btn" data-action="reveal">Show Solution</button>'
        f"</div>"
        f'<div class="lab-feedback" role="status" aria-live="polite" hidden></div>'
        f"</div>"
        f"</section>"
    )


def render_verify_block(
    attr_str: str,
    inner: str,
    placeholders: list[str],
    widget_resolver: Any,
) -> str:
    attrs = parse_attrs(attr_str)
    v_id = attrs.get("id", "verify-0001")
    title = attrs.get("title", "Verification Lab")
    badge = attrs.get("badge", "Dual Verification")

    checklist_items: list[str] = []
    remaining_lines: list[str] = []
    for line in inner.splitlines():
        m = re.match(r"^\s*-\s*\[\s*\]\s+(.+)$", line)
        if m:
            checklist_items.append(m.group(1).strip())
        else:
            remaining_lines.append(line)

    body_html = render_markdown_fragment(
        "\n".join(remaining_lines), placeholders, widget_resolver
    )

    checks_html = ""
    if checklist_items:
        items_rendered: list[str] = []
        for idx, item_md in enumerate(checklist_items, start=1):
            cb_id = f"{v_id}-check-{idx}"
            item_html = render_inline_md(rewrite_md_links(item_md))
            items_rendered.append(
                f'<label class="verify-item" for="{html.escape(cb_id)}">'
                f'<input type="checkbox" id="{html.escape(cb_id)}" />'
                f"<span>{item_html}</span>"
                f"</label>"
            )
        checks_html = (
            '<div class="verify-checklist" role="group" '
            f'aria-label="Verification steps for {html.escape(title)}">'
            + "".join(items_rendered)
            + "</div>"
        )

    return (
        f'<section class="lab-panel verify-panel" id="{html.escape(v_id)}" '
        f'aria-labelledby="{html.escape(v_id)}-title">'
        f'<div class="lab-header">'
        f'<h3 id="{html.escape(v_id)}-title">{html.escape(title)}</h3>'
        f'<span class="lab-badge">{html.escape(badge)}</span>'
        f"</div>"
        f'<div class="lab-body">{body_html}{checks_html}</div>'
        f"</section>"
    )


def render_quiz_block(
    attr_str: str,
    inner: str,
    source_path: Path,
    quiz_errors: list[str],
) -> str:
    attrs = parse_attrs(attr_str)
    q_id = attrs.get("id", "quiz-0001")
    title = attrs.get("title", "Retrieval Practice")
    badge = attrs.get("badge", "3 Questions • Equal-Length Options")

    questions = yaml.safe_load(inner) or []
    q_blocks: list[str] = []

    for q_idx, q in enumerate(questions, start=1):
        q_text = str(q.get("question", ""))
        wrong_hint = str(q.get("wrong_hint", ""))
        options = q.get("options") or []
        if len(options) != 4:
            quiz_errors.append(
                f"{source_path} ({q_id} Q{q_idx}): Expected 4 options, found {len(options)}"
            )

        word_counts: list[int] = []
        opt_buttons: list[str] = []
        for opt in options:
            letter = str(opt.get("letter", "A"))
            text = str(opt.get("text", "")).strip()
            correct = bool(opt.get("correct", False))
            explain = str(opt.get("explain", "")).strip()
            words = text.split()
            word_counts.append(len(words))
            opt_buttons.append(
                f'<button type="button" class="quiz-option-btn" '
                f'data-correct="{"true" if correct else "false"}" '
                f'data-explain="{html.escape(explain, quote=True)}">'
                f'<span class="quiz-opt-letter">{html.escape(letter)}.</span>'
                f"<span>{render_inline_md(text)}</span>"
                f"</button>"
            )

        if len(set(word_counts)) > 1:
            quiz_errors.append(
                f"{source_path} ({q_id} Q{q_idx}): Quiz options must have identical word counts, got {word_counts}"
            )

        q_blocks.append(
            f'<div class="quiz-question" data-wrong-hint="{html.escape(wrong_hint, quote=True)}">'
            f'<p class="quiz-q-title">{q_idx}. {render_inline_md(q_text)}</p>'
            f'<div class="quiz-options">{"".join(opt_buttons)}</div>'
            f'<div class="lab-feedback" role="status" aria-live="polite" hidden></div>'
            f"</div>"
        )

    return (
        f'<section class="lab-panel quiz-panel" id="{html.escape(q_id)}" '
        f'aria-labelledby="{html.escape(q_id)}-title">'
        f'<div class="lab-header">'
        f'<h3 id="{html.escape(q_id)}-title">{html.escape(title)}</h3>'
        f'<span class="lab-badge">{html.escape(badge)}</span>'
        f"</div>"
        f'<div class="lab-body">{"".join(q_blocks)}</div>'
        f"</section>"
    )


def render_document_body(
    body_md: str,
    source_path: Path,
    widget_resolver: Any,
    quiz_errors: list[str],
) -> str:
    placeholders: list[str] = []

    def _stash_block(html_fragment: str) -> str:
        idx = len(placeholders)
        placeholders.append(html_fragment)
        return f"\n\n<!--FENCED_CODE_PLACEHOLDER_{idx}-->\n\n"

    # 1. Extract :::exercise ... ::: (note: may contain nested :::prompts ... :::)
    ex_pattern = re.compile(
        r"^:::exercise[ \t]+([^\n]+)\n(.*?)\n^:::[ \t]*$",
        re.MULTILINE | re.DOTALL,
    )
    # Because :::exercise can contain :::prompts ... :::, match carefully
    pos = 0
    out_chunks: list[str] = []
    lines = body_md.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        line = lines[i]
        m_open = re.match(
            r"^:::(exercise|verify|quiz|callout(?:-[a-z]+)?|teacher-prompt)(?:[ \t]+([^\n]*))?\n?$",
            line,
        )
        if not m_open:
            out_chunks.append(line)
            i += 1
            continue

        kind = m_open.group(1)
        attr_str = (m_open.group(2) or "").strip()
        i += 1
        inner_lines: list[str] = []
        in_nested_prompts = False
        while i < len(lines):
            cur = lines[i]
            if kind == "exercise" and re.match(r"^:::prompts[ \t]*$", cur.strip()):
                in_nested_prompts = True
                inner_lines.append(cur)
                i += 1
                continue
            if re.match(r"^:::[ \t]*$", cur.strip()):
                if in_nested_prompts:
                    in_nested_prompts = False
                    inner_lines.append(cur)
                    i += 1
                    continue
                i += 1
                break
            inner_lines.append(cur)
            i += 1

        inner_text = "".join(inner_lines)
        if kind == "exercise":
            out_chunks.append(
                _stash_block(
                    render_exercise_block(attr_str, inner_text, placeholders, widget_resolver)
                )
            )
        elif kind == "verify":
            out_chunks.append(
                _stash_block(
                    render_verify_block(attr_str, inner_text, placeholders, widget_resolver)
                )
            )
        elif kind == "quiz":
            out_chunks.append(
                _stash_block(
                    render_quiz_block(attr_str, inner_text, source_path, quiz_errors)
                )
            )
        elif kind == "teacher-prompt":
            inner_html = render_markdown_fragment(
                inner_text, placeholders, widget_resolver
            )
            out_chunks.append(
                _stash_block(f'<aside class="teacher-prompt" aria-label="Teacher Prompt">{inner_html}</aside>')
            )
        else:
            # callout, callout-warn, callout-success
            extra_cls = f" {kind}" if kind != "callout" else ""
            inner_html = render_markdown_fragment(
                inner_text, placeholders, widget_resolver
            )
            out_chunks.append(
                _stash_block(f'<div class="callout{extra_cls}">{inner_html}</div>')
            )

    transformed_md = "".join(out_chunks)
    rendered_html = render_markdown_fragment(
        transformed_md, placeholders, widget_resolver
    )

    # Restore all placeholders (multiple passes in case nested placeholders exist)
    for _ in range(4):
        if "<!--FENCED_CODE_PLACEHOLDER_" not in rendered_html:
            break

        def _restore(m: re.Match[str]) -> str:
            return placeholders[int(m.group(1))]

        rendered_html = re.sub(
            r"<p>\s*<!--FENCED_CODE_PLACEHOLDER_(\d+)-->\s*</p>",
            _restore,
            rendered_html,
        )
        rendered_html = re.sub(
            r"<!--FENCED_CODE_PLACEHOLDER_(\d+)-->",
            _restore,
            rendered_html,
        )

    return rendered_html


def build_lesson_cards_html(lessons: list[dict[str, Any]], rel_prefix: str) -> str:
    cards: list[str] = []
    for item in lessons:
        num = item["num"]
        badge = str(item["meta"].get("badge", ""))
        # Strip any leading "Lesson NNNN •" prefix to prevent duplication
        clean_badge = re.sub(
            r"^Lesson\s+\d+\s*[•·:-]\s*", "", badge, flags=re.IGNORECASE
        ).strip()
        meta_line = f"LESSON {num}" + (f" • {clean_badge}" if clean_badge else "")
        card_meta = item["meta"].get("card") or {}
        card_title_md = str(card_meta.get("title") or item["meta"].get("title", ""))
        card_summary_md = str(
            card_meta.get("summary") or item["meta"].get("subtitle", "")
        )
        href = f"{rel_prefix}lessons/{item['slug']}.html"
        cards.append(
            f'<a class="lesson-card" href="{html.escape(href)}">'
            f"<div>"
            f'<div class="lesson-card-meta">{html.escape(meta_line)}</div>'
            f"<h3>{render_inline_md(card_title_md)}</h3>"
            f"<p>{render_inline_md(card_summary_md)}</p>"
            f"</div>"
            f"</a>"
        )
    return '<div class="card-grid">' + "".join(cards) + "</div>"


def build_reference_cards_html(refs: list[dict[str, Any]], rel_prefix: str) -> str:
    cards: list[str] = []
    for ref in refs:
        card_meta = ref["meta"].get("card") or {}
        title_md = str(card_meta.get("title") or ref["meta"].get("title", ""))
        summary_md = str(card_meta.get("summary") or ref["meta"].get("subtitle", ""))
        badge = str(ref["meta"].get("badge", "Reference"))
        href = f"{rel_prefix}reference/{ref['html_name']}"
        cards.append(
            f'<a class="ref-card" href="{html.escape(href)}">'
            f"<div>"
            f'<div class="lesson-card-meta">{html.escape(badge)}</div>'
            f"<h3>{render_inline_md(title_md)}</h3>"
            f"<p>{render_inline_md(summary_md)}</p>"
            f"</div>"
            f"</a>"
        )
    return '<div class="card-grid">' + "".join(cards) + "</div>"


def build_nav_html(
    page_kind: str,
    meta: dict[str, Any],
    lessons: list[dict[str, Any]],
    refs: list[dict[str, Any]],
    rel_prefix: str,
    lesson_idx: int | None = None,
) -> str:
    index_href = f"{rel_prefix}index.html"
    if page_kind == "index":
        crumbs = '<span class="nav-current" aria-current="page">Index</span>'
    elif page_kind == "lesson" and lesson_idx is not None:
        num = lessons[lesson_idx]["num"]
        crumbs = (
            f'<a href="{html.escape(index_href)}">Index</a>'
            f'<span class="nav-sep" aria-hidden="true">›</span>'
            f'<span class="nav-current" aria-current="page">Lesson {html.escape(num)}</span>'
        )
    else:
        label = str(meta.get("nav_label") or meta.get("title", "Reference"))
        crumbs = (
            f'<a href="{html.escape(index_href)}">Index</a>'
            f'<span class="nav-sep" aria-hidden="true">›</span>'
            f'<span class="nav-current" aria-current="page">{html.escape(label)}</span>'
        )

    pager_html = ""
    if page_kind == "lesson" and lesson_idx is not None:
        prev_item = lessons[lesson_idx - 1] if lesson_idx > 0 else None
        next_item = (
            lessons[lesson_idx + 1] if lesson_idx + 1 < len(lessons) else None
        )
        if prev_item:
            prev_link = (
                f'<a class="nav-pager-link" '
                f'href="{html.escape(rel_prefix)}lessons/{html.escape(prev_item["slug"])}.html" '
                f'title="Previous: Lesson {html.escape(prev_item["num"])} — {html.escape(prev_item["meta"].get("title", ""))}">'
                f"← Prev</a>"
            )
        else:
            prev_link = '<span class="nav-pager-link" aria-disabled="true">← Prev</span>'

        if next_item:
            next_link = (
                f'<a class="nav-pager-link" '
                f'href="{html.escape(rel_prefix)}lessons/{html.escape(next_item["slug"])}.html" '
                f'title="Next: Lesson {html.escape(next_item["num"])} — {html.escape(next_item["meta"].get("title", ""))}">'
                f"Next →</a>"
            )
        else:
            next_link = '<span class="nav-pager-link" aria-disabled="true">Next →</span>'

        pager_html = (
            f'<span class="nav-pager-group" role="group" aria-label="Lesson navigation">'
            f"{prev_link}<span>·</span>{next_link}"
            f"</span>"
            f'<span class="nav-divider" aria-hidden="true">|</span>'
        )

    ref_links: list[str] = []
    cur_nav_id = meta.get("nav_id")
    for ref in refs:
        r_label = str(ref["meta"].get("nav_label") or ref["meta"].get("title"))
        r_href = f"{rel_prefix}reference/{ref['html_name']}"
        is_cur = (
            ' aria-current="page"'
            if page_kind == "reference" and ref["meta"].get("nav_id") == cur_nav_id
            else ""
        )
        ref_links.append(
            f'<a class="nav-ref-link" href="{html.escape(r_href)}"{is_cur}>{html.escape(r_label)}</a>'
        )

    return (
        '<header class="site-header">'
        '<a class="skip-link visually-hidden" href="#main-title">Skip to main content</a>'
        '<nav class="course-nav" aria-label="Primary">'
        f'<div class="nav-breadcrumbs">{crumbs}</div>'
        '<div class="nav-controls">'
        f"{pager_html}"
        f'{"".join(ref_links)}'
        '<span class="mission-badge">Spotykach Firmware</span>'
        "</div>"
        "</nav>"
        "</header>"
    )


def build_lesson_pager_html(
    lessons: list[dict[str, Any]], lesson_idx: int, rel_prefix: str
) -> str:
    prev_item = lessons[lesson_idx - 1] if lesson_idx > 0 else None
    next_item = lessons[lesson_idx + 1] if lesson_idx + 1 < len(lessons) else None

    cards: list[str] = []
    if prev_item:
        cards.append(
            f'<a class="pager-card is-prev" href="{html.escape(rel_prefix)}lessons/{html.escape(prev_item["slug"])}.html">'
            f'<span class="pager-label">← Previous • Lesson {html.escape(prev_item["num"])}</span>'
            f'<span class="pager-title">{html.escape(prev_item["meta"].get("title", ""))}</span>'
            f"</a>"
        )
    else:
        cards.append(
            f'<a class="pager-card is-prev" href="{html.escape(rel_prefix)}index.html">'
            f'<span class="pager-label">← Course Overview</span>'
            f'<span class="pager-title">Return to Course Index</span>'
            f"</a>"
        )

    if next_item:
        cards.append(
            f'<a class="pager-card is-next" href="{html.escape(rel_prefix)}lessons/{html.escape(next_item["slug"])}.html">'
            f'<span class="pager-label">Next • Lesson {html.escape(next_item["num"])} →</span>'
            f'<span class="pager-title">{html.escape(next_item["meta"].get("title", ""))}</span>'
            f"</a>"
        )
    else:
        cards.append(
            f'<a class="pager-card is-next" href="{html.escape(rel_prefix)}reference/hardware-architecture.html">'
            f'<span class="pager-label">Reference Sheet →</span>'
            f'<span class="pager-title">Spotykach Hardware &amp; STM32H750 Architecture</span>'
            f"</a>"
        )

    return (
        '<nav class="lesson-pager" aria-label="Lesson pagination">'
        + "".join(cards)
        + "</nav>"
    )


def wrap_html_document(
    meta: dict[str, Any],
    nav_html: str,
    body_html: str,
    pager_html: str,
    rel_prefix: str,
) -> str:
    page_title = str(meta.get("page_title") or meta.get("title", "Spotykach Course"))
    h1_title = str(meta.get("title", "Spotykach Firmware"))
    badge = str(meta.get("badge", "Spotykach Firmware Course"))
    subtitle = str(meta.get("subtitle", ""))

    subtitle_html = (
        f'<p class="page-subtitle">{render_inline_md(subtitle)}</p>'
        if subtitle
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="color-scheme" content="dark" />
  <title>{html.escape(page_title)}</title>
  <link rel="stylesheet" href="{html.escape(rel_prefix)}assets/style.css" />
</head>
<body>
  {nav_html}
  <main class="page-shell">
    <article class="tufte-article">
      <header class="page-hero">
        <div class="page-badge">{html.escape(badge)}</div>
        <h1 id="main-title" tabindex="-1">{render_inline_md(h1_title)}</h1>
        {subtitle_html}
      </header>
      {body_html}
      {pager_html}
    </article>
  </main>
  <footer class="site-footer">
    <p>Spotykach Firmware Engineering Course • Grounded in the official Synthux Academy Spotykach repository (`STM32H750IB` / `libDaisy` / `DaisySP`).</p>
  </footer>
  <script src="{html.escape(rel_prefix)}assets/course.js"></script>
</body>
</html>
"""


def validate_html_output(
    html_text: str, out_path: Path, out_root: Path, errors: list[str]
) -> None:
    # 1. Check that no <pre><code...> contains <p>, <h1..6>, or nested <pre>
    for m in re.finditer(
        r"<pre><code[^>]*>(.*?)</code></pre>", html_text, flags=re.DOTALL
    ):
        code_inner = m.group(1)
        if re.search(r"<(p|h[1-6]|pre)\b", code_inner, flags=re.IGNORECASE):
            errors.append(
                f"{out_path}: Corrupted <pre><code> block contains HTML block tags (<p>, <h1..6>, or <pre>)"
            )

    # 2. Check for leaked raw directives or tokens outside code blocks
    stripped_code = re.sub(
        r"<pre\b[^>]*>.*?</pre>|<code\b[^>]*>.*?</code>",
        "",
        html_text,
        flags=re.DOTALL,
    )
    if re.search(r"\{\{(sidenote|widget|blank):", stripped_code):
        errors.append(f"{out_path}: Unexpanded {{{{...}}}} directive leaked into HTML")
    if "{#" in stripped_code:
        errors.append(f"{out_path}: Raw {{#anchor}} token leaked into HTML")
    if "<!--FENCED_CODE_PLACEHOLDER_" in html_text:
        errors.append(f"{out_path}: Unrestored code placeholder leaked into HTML")

    # 3. Validate internal links
    for m in re.finditer(r'href="([^"]+)"', html_text):
        href = m.group(1)
        if href.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target_rel = href.split("#", 1)[0]
        if not target_rel:
            continue
        target_path = (out_path.parent / target_rel).resolve()
        if not target_path.exists():
            errors.append(
                f"{out_path}: Broken internal link '{href}' (expected {target_path})"
            )


def build_site(out_dir: Path, check: bool = False) -> int:
    lessons_dir = ROOT_DIR / "lessons"
    ref_dir = ROOT_DIR / "reference"
    index_md_path = ROOT_DIR / "index.md"

    lessons: list[dict[str, Any]] = []
    for p in sorted(lessons_dir.glob("*.md")):
        meta, body = parse_frontmatter(p.read_text(encoding="utf-8"), p)
        m_num = re.match(r"^(\d{4})-(.+)$", p.stem)
        num = m_num.group(1) if m_num else "0001"
        lessons.append({"path": p, "slug": p.stem, "num": num, "meta": meta, "body": body})

    refs: list[dict[str, Any]] = []
    # Keep GLOSSARY first, then alphabetical
    ref_paths = sorted(
        ref_dir.glob("*.md"),
        key=lambda x: (0 if x.name == "GLOSSARY.md" else 1, x.name),
    )
    for p in ref_paths:
        meta, body = parse_frontmatter(p.read_text(encoding="utf-8"), p)
        html_name = "glossary.html" if p.name == "GLOSSARY.md" else f"{p.stem}.html"
        refs.append({"path": p, "html_name": html_name, "meta": meta, "body": body})

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "lessons").mkdir(parents=True, exist_ok=True)
    (out_dir / "reference").mkdir(parents=True, exist_ok=True)

    if out_dir.resolve() != ROOT_DIR.resolve():
        out_assets = out_dir / "assets"
        if out_assets.exists():
            shutil.rmtree(out_assets)
        shutil.copytree(ROOT_DIR / "assets", out_assets)
        (out_dir / ".nojekyll").write_text("", encoding="utf-8")

    quiz_errors: list[str] = []
    generated_files: list[Path] = []

    def make_widget_resolver(rel_prefix: str) -> Any:
        def _resolve(widget_id: str) -> str:
            if widget_id == "lesson-cards":
                return build_lesson_cards_html(lessons, rel_prefix)
            if widget_id == "reference-cards":
                return build_reference_cards_html(refs, rel_prefix)
            return f'<div data-widget="{html.escape(widget_id)}"></div>'

        return _resolve

    # Build index.md -> index.html
    idx_meta, idx_body = parse_frontmatter(
        index_md_path.read_text(encoding="utf-8"), index_md_path
    )
    idx_nav = build_nav_html("index", idx_meta, lessons, refs, rel_prefix="")
    idx_body_html = render_document_body(
        idx_body, index_md_path, make_widget_resolver(""), quiz_errors
    )
    idx_html = wrap_html_document(idx_meta, idx_nav, idx_body_html, "", rel_prefix="")
    idx_out = out_dir / "index.html"
    idx_out.write_text(idx_html, encoding="utf-8")
    generated_files.append(idx_out)

    # Build lessons/*.md -> lessons/*.html
    for l_idx, item in enumerate(lessons):
        l_nav = build_nav_html(
            "lesson", item["meta"], lessons, refs, rel_prefix="../", lesson_idx=l_idx
        )
        l_body_html = render_document_body(
            item["body"],
            item["path"],
            make_widget_resolver("../"),
            quiz_errors,
        )
        l_pager = build_lesson_pager_html(lessons, l_idx, rel_prefix="../")
        l_html = wrap_html_document(
            item["meta"], l_nav, l_body_html, l_pager, rel_prefix="../"
        )
        l_out = out_dir / "lessons" / f"{item['slug']}.html"
        l_out.write_text(l_html, encoding="utf-8")
        generated_files.append(l_out)

    # Build reference/*.md -> reference/*.html
    for ref in refs:
        r_nav = build_nav_html(
            "reference", ref["meta"], lessons, refs, rel_prefix="../"
        )
        r_body_html = render_document_body(
            ref["body"],
            ref["path"],
            make_widget_resolver("../"),
            quiz_errors,
        )
        r_html = wrap_html_document(
            ref["meta"], r_nav, r_body_html, "", rel_prefix="../"
        )
        r_out = out_dir / "reference" / ref["html_name"]
        r_out.write_text(r_html, encoding="utf-8")
        generated_files.append(r_out)

    errors: list[str] = list(quiz_errors)
    if check:
        for out_path in generated_files:
            validate_html_output(
                out_path.read_text(encoding="utf-8"), out_path, out_dir, errors
            )

    if errors:
        for err in errors:
            print(f"[ERROR] {err}", file=sys.stderr)
        return 1

    print(
        f"[OK] Built and verified {len(generated_files)} HTML pages in {out_dir.relative_to(ROOT_DIR.parent) if out_dir.is_relative_to(ROOT_DIR.parent) else out_dir}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Spotykach tutorial site.")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT_DIR,
        help="Output directory for generated HTML files.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate HTML output, internal links, and equal-word-count quiz options.",
    )
    args = parser.parse_args()
    return build_site(args.out_dir.resolve(), check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
