#!/usr/bin/env python3
"""Copy a paper explainer from the Obsidian vault into this site.

The note is written in plain Obsidian markdown. This turns the Obsidian-only
pieces into what the site needs:

  (p. 4)  (pp. 4-5)            -> a "p. 4" chip that opens the paper at that page
  ![[diagram.svg|caption]]     -> the image, copied into the page bundle
  a YouTube link on its own line, or ![](youtube link) -> an embedded video
  %% private note %%           -> removed (never published)
  [[link|text]]                -> text
  > [!note] Title              -> > **Title**

Math ($...$, $$...$$) and ```mermaid blocks pass through unchanged.

The page's frontmatter (the paper's metadata) stays in
content/papers/<slug>/index.md; only the body is replaced.

Usage:
  scripts/from_vault.py <vault-note.md> <slug>            # preview as a draft
  scripts/from_vault.py <vault-note.md> <slug> --publish  # draft: false, date = today
"""

import argparse
import datetime as dt
import re
import shutil
import sys
from pathlib import Path

VAULT = Path("/home/dk/vaults")
SITE = Path(__file__).resolve().parent.parent

YOUTUBE = re.compile(r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/|shorts/|live/))([\w-]{11})")
PAGE_REF = re.compile(r"\((pp?)\.\s?(\d+)(?:\s?[-–]\s?\d+)?\)")
EMBED = re.compile(r"!\[\[([^\]|#]+)(?:\|([^\]]*))?\]\]")
WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]*))?\]\]")
CALLOUT = re.compile(r"^(\s*>\s*)\[!(\w+)\][+-]?\s*(.*)$")
FRONTMATTER = re.compile(r"\A---\n.*?\n---\n?", re.S)


def find_attachment(name: str, note: Path) -> Path | None:
    for candidate in (note.parent / name, note.parent / "assets" / name, VAULT / "assets" / name):
        if candidate.is_file():
            return candidate
    hits = [p for p in VAULT.rglob(name) if ".trash" not in p.parts]
    return hits[0] if hits else None


def convert(text: str, note: Path, bundle: Path, stats: dict) -> str:
    text = FRONTMATTER.sub("", text, count=1)
    text = re.sub(r"%%.*?%%", "", text, flags=re.S)

    out, in_fence = [], False
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue

        stripped = line.strip()
        bare = re.fullmatch(r"!?\[[^\]]*\]\((\S+)\)|<?(\S+?)>?", stripped)
        url = bare and (bare.group(1) or bare.group(2))
        if url and YOUTUBE.search(url):
            out.append('{{< video youtube="%s" >}}' % YOUTUBE.search(url).group(1))
            stats["videos"] += 1
            continue

        def embed(m):
            name, caption = m.group(1).strip(), (m.group(2) or "").strip()
            src = find_attachment(name, note)
            if not src:
                stats["missing"].append(name)
                return m.group(0)
            shutil.copy2(src, bundle / src.name)
            stats["images"] += 1
            if caption.isdigit():  # Obsidian's ![[img.png|300]] is a width, not a caption
                caption = ""
            return f"![{caption}]({src.name})"

        line = EMBED.sub(embed, line)
        line = WIKILINK.sub(lambda m: (m.group(2) or m.group(1)).strip(), line)

        def page_ref(m):
            stats["page_refs"] += 1
            return "{{< p %s >}}" % m.group(2)

        line = PAGE_REF.sub(page_ref, line)

        c = CALLOUT.match(line)
        if c:
            title = c.group(3).strip() or c.group(2).capitalize()
            line = f"{c.group(1)}**{title}**"
        out.append(line)

    return "\n".join(out).strip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("note", type=Path)
    ap.add_argument("slug")
    ap.add_argument("--publish", action="store_true")
    args = ap.parse_args()

    note = args.note.resolve()
    bundle = SITE / "content" / "papers" / args.slug
    index = bundle / "index.md"
    if not note.is_file():
        sys.exit(f"no such note: {note}")
    if not index.is_file():
        sys.exit(f"no page at {index} — create it with the paper's frontmatter first")

    page = index.read_text()
    fm = FRONTMATTER.match(page)
    if not fm:
        sys.exit(f"{index} has no frontmatter")
    head = fm.group(0)
    if args.publish:
        head = re.sub(r"^draft:.*$", "draft: false", head, flags=re.M)
        head = re.sub(r"^date:.*$", f"date: {dt.date.today().isoformat()}", head, flags=re.M)

    stats = {"page_refs": 0, "images": 0, "videos": 0, "missing": []}
    body = convert(note.read_text(), note, bundle, stats)
    index.write_text(head.rstrip("\n") + "\n\n" + body)

    words = len(re.findall(r"\w+", re.sub(r"\{\{<.*?>\}\}", "", body)))
    print(f"{index.relative_to(SITE)}: {words} words, {stats['page_refs']} page refs, "
          f"{stats['images']} images, {stats['videos']} videos"
          + (" — PUBLISH" if args.publish else " — draft"))
    if stats["missing"]:
        print("attachments not found in the vault: " + ", ".join(stats["missing"]))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
