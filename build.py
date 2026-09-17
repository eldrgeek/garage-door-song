"""Build index.html from the song timing, the narration, credits.json and template.html.

- timed-lyrics.srt is the lyric track embedded in Suno's download of the song,
  so each lyric line carries the time it is sung.
- narration.json is the narrated "How they did it" section; build-narration.py
  renders it to audio/narration.mp3 and writes audio/narration-timing.json.
- credits.json holds one entry per image: the lyric section it illustrates, who
  wrote the prompt, which model made the image, and the exact prompt.

Every element that should line up with audio gets data-track ("song" or
"story") and data-t (seconds). The page scrolls to those elements as the audio
plays, and seeks the audio when the reader scrolls to them.
Run: python3 build.py
"""
import html, json, re
from pathlib import Path

ROOT = Path(__file__).parent
credits = json.loads((ROOT / "credits.json").read_text())
scenes = credits["scenes"]
PROMPTERS = credits["prompters"]
MAKERS = credits["makers"]
narration = json.loads((ROOT / "narration.json").read_text())
ntiming = json.loads((ROOT / "audio/narration-timing.json").read_text())
SONG_DURATION = 207.6
STORY_DURATION = ntiming["duration"]
esc = html.escape


def srt_time(s):
    h, m, rest = s.split(":")
    sec, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000


# --- Song sections from the SRT -------------------------------------------
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
        <img src="img/{sid}.jpg" alt="{esc(s['alt'])}" loading="lazy">
        <figcaption>
          <span class="cap-title">{esc(s['title'])}</span>
          <span class="cap-credit">Prompt by <b style="--c:{p['color']}">{p['name']}</b> · Image by <b style="--c:{mk['color']}">{mk['name']}</b></span>
          <details><summary>Read the prompt</summary><p>{esc(s['prompt'])}</p></details>
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
        f'<p class="ly cue" data-track="song" data-t="{a:.3f}" data-i="{i}">{esc(t)}</p>'
        for i, (a, b, t) in enumerate(sec["lines"])
    )
    direction = f'<span class="direction">{esc(sec["direction"])}</span>' if sec["direction"] else ""
    head = (f'<h3 data-track="song" data-t="{sec["start"]:.3f}"><span class="sec-time">{fmt(sec["start"])}</span>'
            f'{esc(sec["label"])}{direction}</h3>')
    if figs:
        # Each picture takes an equal share of the section's lines, in order.
        stage = "".join(figure(sid, f'data-from="{i * n // k}"') for i, sid in enumerate(figs))
        song_html.append(f"""
  <section class="song-sec scrolly {kind}" data-label="{esc(sec['label'])}">
    <div class="lines">{head}{lines}</div>
    <div class="stage"><div class="stage-inner">{stage}</div></div>
  </section>""")
    else:
        song_html.append(f"""
  <section class="song-sec plain {kind}" data-label="{esc(sec['label'])}">
    <div class="lines">{head}{lines}</div>
  </section>""")

intro = next(s for s in sections if s["label"] == "Intro")
intro_lines = {t: a for a, b, t in intro["lines"]}

# --- Narration --------------------------------------------------------------
speakers = narration["speakers"]
tmap = {x["id"]: x for x in ntiming["lines"]}
story_lines, story_imgs = [], []
for ln in narration["lines"]:
    sp = speakers[ln["speaker"]]
    t = tmap[ln["id"]]
    story_lines.append(
        f'<div class="nl cue" data-track="story" data-t="{t["start"]:.3f}" data-img="{ln["image"]}">'
        f'<span class="who" style="--c:{sp["color"]}">{esc(sp["name"])}<small>{esc(sp["org"])}</small></span>'
        f'<p>{esc(ln["text"])}</p></div>')
    if ln["image"] not in story_imgs:
        story_imgs.append(ln["image"])


def story_figure(key):
    if key == "suno-cover":
        return ('<figure class="scene" data-key="suno-cover"><img src="img/suno-cover.jpg" alt="Suno\'s crayon cover art for Garage Door" loading="lazy">'
                '<figcaption><span class="cap-title">Cover art for “Garage Door”</span><span class="cap-credit">Made by <b style="--c:#c7a6ff">Suno</b></span></figcaption></figure>')
    return figure(key, f'data-key="{key}"').replace(f'id="{key}"', f'id="story-{key}"')


story_html = f"""
  <section class="story scrolly" data-label="How they did it">
    <div class="lines">{''.join(story_lines)}</div>
    <div class="stage" data-mode="bykey"><div class="stage-inner">{''.join(story_figure(k) for k in story_imgs)}</div></div>
  </section>"""

authors = {}
for ln in narration["lines"]:
    authors.setdefault(ln["speaker"], set()).add(ln["author"])
narr_credits = "".join(
    f'<li><b>{esc(sp["name"])}</b>: voice “{esc(sp["voiceName"])}” (ElevenLabs), '
    f'lines by {", ".join(esc(speakers[a]["name"] if a in speakers else a) for a in sorted(authors.get(key, [])))}</li>'
    for key, sp in speakers.items())

# --- Credit matrix: prompt writer x image maker --------------------------------
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
    "{{STORY}}": story_html,
    "{{NARRATION_CREDITS}}": narr_credits,
    "{{MATRIX_HEAD}}": matrix_head,
    "{{MATRIX_ROWS}}": "\n".join(matrix_rows),
    "{{HERO_CREDIT}}": f"Prompt by {PROMPTERS[scenes['s3']['prompter']]['name']} · Image by {MAKERS[scenes['s3']['maker']]['name']}",
    "{{S1}}": figure("s1"),
    "{{T_TURN}}": f'{intro_lines["Turn it down!"]:.3f}',
    "{{T_NAH}}": f'{intro_lines["Nah."]:.3f}',
    "{{T_VERSE1}}": f'{next(s for s in sections if s["label"] == "Verse 1")["start"]:.3f}',
    "{{SONG_DURATION}}": f"{SONG_DURATION}",
    "{{STORY_DURATION}}": f"{STORY_DURATION}",
    "{{LAST_LINE_END}}": f'{ntiming["lines"][-1]["end"]:.3f}',
}
page = (ROOT / "template.html").read_text()
for k, v in subs.items():
    page = page.replace(k, v)
assert "{{" not in page, "unfilled placeholder: " + page[page.index("{{"):page.index("{{") + 30]
(ROOT / "index.html").write_text(page)
print(f"wrote index.html: {len(sections)} song sections, {len(story_lines)} narration lines, story {STORY_DURATION:.1f}s")
