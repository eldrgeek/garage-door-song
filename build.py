"""Build index.html from lyrics.txt and credits.json.

credits.json holds one entry per scene image: which lyric section it illustrates,
who wrote the prompt, which model made the image, and the exact prompt used.
Run: python3 build.py
"""
import html, json, re
from pathlib import Path

ROOT = Path(__file__).parent
credits = json.loads((ROOT / "credits.json").read_text())
scenes = credits["scenes"]
PROMPTERS = credits["prompters"]
MAKERS = credits["makers"]

# Lyrics: split on [Section] tags.
sections = []
for block in re.split(r"\n(?=\[)", (ROOT / "lyrics.txt").read_text().strip()):
    m = re.match(r"\[(.+?)\]\n?(.*)", block, re.S)
    if m:
        sections.append((m.group(1), [l for l in m.group(2).strip().split("\n") if l.strip()]))

SECTION_SCENES = {}
for sid, s in scenes.items():
    SECTION_SCENES.setdefault(s["section"], []).append(sid)


def figure(sid, cls=""):
    s = scenes[sid]
    p, mk = PROMPTERS[s["prompter"]], MAKERS[s["maker"]]
    return f"""
    <figure class="scene {cls}" id="{sid}">
      <img src="img/{sid}.jpg" alt="{html.escape(s['alt'])}" loading="lazy">
      <figcaption>
        <span class="cap-title">{html.escape(s['title'])}</span>
        <span class="cap-credit">Prompt by <b style="--c:{p['color']}">{p['name']}</b> · Image by <b style="--c:{mk['color']}">{mk['name']}</b></span>
        <details><summary>Read the prompt</summary><p>{html.escape(s['prompt'])}</p></details>
      </figcaption>
    </figure>"""


def lyric_section(name, lines):
    label, _, direction = name.partition(":")
    body = "\n".join(f"<p>{html.escape(l)}</p>" for l in lines)
    # pop: a section name that repeats (the Hook) shows its pictures only the first time.
    figs = "".join(figure(sid) for sid in SECTION_SCENES.pop(label.strip(), []))
    dir_html = f'<span class="direction">{html.escape(direction.strip())}</span>' if direction else ""
    kind = "hook" if "Hook" in label else ("verse" if "Verse" in label else "small")
    return f"""
  <section class="lyric {kind}">
    <div class="lyric-text">
      <h3>{html.escape(label.strip())}{dir_html}</h3>
      {body}
    </div>
    <div class="lyric-figs">{figs}</div>
  </section>"""


lyrics_html = "".join(lyric_section(n, l) for n, l in sections)

# Credit matrix: prompter x maker.
matrix_rows = []
for pk, p in PROMPTERS.items():
    cells = []
    for mk in MAKERS:
        ids = [sid for sid, s in scenes.items() if s["prompter"] == pk and s["maker"] == mk]
        cells.append("<td>" + " ".join(f'<a href="#{i}"><img src="img/{i}.jpg" alt=""></a>' for i in ids) + "</td>")
    matrix_rows.append(f'<tr><th style="--c:{p["color"]}">{p["name"]}<small>{p["via"]}</small></th>{"".join(cells)}</tr>')
matrix_head = "".join(f'<th style="--c:{m["color"]}">{m["name"]}<small>{m["via"]}</small></th>' for m in MAKERS.values())

page = (ROOT / "template.html").read_text()
page = page.replace("{{LYRICS}}", lyrics_html)
page = page.replace("{{MATRIX_HEAD}}", matrix_head).replace("{{MATRIX_ROWS}}", "\n".join(matrix_rows))
page = page.replace("{{HERO_CREDIT}}", f"Prompt by {PROMPTERS[scenes['s3']['prompter']]['name']} · Image by {MAKERS[scenes['s3']['maker']]['name']}")
page = page.replace("{{S1}}", figure("s1", "wide"))
(ROOT / "index.html").write_text(page)
print("wrote index.html,", len(scenes), "scenes")
