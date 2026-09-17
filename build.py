"""Build index.html from timed-lyrics.srt, credits.json and template.html.

timed-lyrics.srt is the lyric track embedded in Suno's download of the song, so
each line carries the time it is sung. The page uses those times to scroll along
with the music and to seek the music when the reader scrolls.
credits.json holds one entry per image: the lyric section it illustrates, who
wrote the prompt, which model made the image, and the exact prompt.
Run: python3 build.py
"""
import html, json, re
from pathlib import Path

ROOT = Path(__file__).parent
credits = json.loads((ROOT / "credits.json").read_text())
scenes = credits["scenes"]
PROMPTERS = credits["prompters"]
MAKERS = credits["makers"]
DURATION = 207.6


def srt_time(s):
    h, m, rest = s.split(":")
    sec, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000


# Parse the SRT into sections: [{label, direction, start, lines: [(start, end, text)]}].
sections = []
for block in re.split(r"\n\s*\n", (ROOT / "timed-lyrics.srt").read_text().strip()):
    rows = block.strip().split("\n")
    if len(rows) < 3:
        continue
    start, end = (srt_time(x.strip()) for x in rows[1].split("-->"))
    text = " ".join(rows[2:]).strip()
    m = re.match(r"\[(.+?)\]$", text)
    if m:
        label, _, direction = m.group(1).partition(":")
        label = label.strip()
        if sections and sections[-1]["label"] == label:
            continue  # Suno repeats [Outro]; keep one section.
        sections.append({"label": label, "direction": direction.strip(), "start": start, "lines": []})
    elif sections:
        sections[-1]["lines"].append((start, end, text))

SECTION_SCENES = {}
for sid, s in scenes.items():
    SECTION_SCENES.setdefault(s["section"], []).append(sid)


def figure(sid, extra=""):
    s = scenes[sid]
    p, mk = PROMPTERS[s["prompter"]], MAKERS[s["maker"]]
    return f"""
      <figure class="scene" id="{sid}" {extra}>
        <img src="img/{sid}.jpg" alt="{html.escape(s['alt'])}" loading="lazy">
        <figcaption>
          <span class="cap-title">{html.escape(s['title'])}</span>
          <span class="cap-credit">Prompt by <b style="--c:{p['color']}">{p['name']}</b> · Image by <b style="--c:{mk['color']}">{mk['name']}</b></span>
          <details><summary>Read the prompt</summary><p>{html.escape(s['prompt'])}</p></details>
        </figcaption>
      </figure>"""


def fmt(t):
    return f"{int(t // 60)}:{int(t % 60):02d}"


song_html = []
for sec in sections:
    if sec["label"] == "Intro":
        continue  # The intro plays under Chapter one, which the template lays out by hand.
    figs = SECTION_SCENES.pop(sec["label"], [])
    n, k = len(sec["lines"]), len(figs)
    kind = "hook" if "Hook" in sec["label"] else ("verse" if "Verse" in sec["label"] else "outro")
    lines = "\n".join(
        f'<p class="ly" data-t="{a:.3f}" data-end="{b:.3f}" data-i="{i}">{html.escape(t)}</p>'
        for i, (a, b, t) in enumerate(sec["lines"])
    )
    direction = f'<span class="direction">{html.escape(sec["direction"])}</span>' if sec["direction"] else ""
    head = f'<h3 data-t="{sec["start"]:.3f}"><span class="sec-time">{fmt(sec["start"])}</span>{html.escape(sec["label"])}{direction}</h3>'
    if figs:
        # Each picture takes an equal share of the section's lines, in order.
        stage = "".join(figure(sid, f'data-from="{i * n // k}"') for i, sid in enumerate(figs))
        song_html.append(f"""
  <section class="song-sec scrolly {kind}" data-label="{html.escape(sec['label'])}">
    <div class="lines">{head}{lines}</div>
    <div class="stage"><div class="stage-inner">{stage}</div></div>
  </section>""")
    else:
        song_html.append(f"""
  <section class="song-sec plain {kind}" data-label="{html.escape(sec['label'])}">
    <div class="lines">{head}{lines}</div>
  </section>""")

intro = next(s for s in sections if s["label"] == "Intro")
intro_lines = {t: (a, b) for a, b, t in intro["lines"]}

# Credit matrix: prompt writer x image maker.
matrix_rows = []
for pk, p in PROMPTERS.items():
    cells = []
    for mk in MAKERS:
        ids = [sid for sid, s in scenes.items() if s["prompter"] == pk and s["maker"] == mk]
        cells.append("<td>" + " ".join(f'<a href="#{i}"><img src="img/{i}.jpg" alt=""></a>' for i in ids) + "</td>")
    matrix_rows.append(f'<tr><th style="--c:{p["color"]}">{p["name"]}<small>{p["via"]}</small></th>{"".join(cells)}</tr>')
matrix_head = "".join(f'<th style="--c:{m["color"]}">{m["name"]}<small>{m["via"]}</small></th>' for m in MAKERS.values())

subs = {
    "{{SONG}}": "".join(song_html),
    "{{MATRIX_HEAD}}": matrix_head,
    "{{MATRIX_ROWS}}": "\n".join(matrix_rows),
    "{{HERO_CREDIT}}": f"Prompt by {PROMPTERS[scenes['s3']['prompter']]['name']} · Image by {MAKERS[scenes['s3']['maker']]['name']}",
    "{{S1}}": figure("s1"),
    "{{T_TURN}}": f'{intro_lines["Turn it down!"][0]:.3f}',
    "{{T_NAH}}": f'{intro_lines["Nah."][0]:.3f}',
    "{{T_VERSE1}}": f'{next(s for s in sections if s["label"] == "Verse 1")["start"]:.3f}',
    "{{DURATION}}": f"{DURATION}",
}
page = (ROOT / "template.html").read_text()
for k, v in subs.items():
    page = page.replace(k, v)
assert "{{" not in page, "unfilled placeholder"
(ROOT / "index.html").write_text(page)
print("wrote index.html:", len(sections), "sections,", sum(len(s["lines"]) for s in sections), "timed lines")
