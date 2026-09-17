"""Render the narrated "How they did it" track.

Reads narration.json, speaks each line with its speaker's ElevenLabs voice
(clips are cached in audio/narr/, so only changed lines are re-rendered), lays
the clips on a timeline, and mixes them over the instrumental bed, which ducks
under the voices. Writes audio/narration.mp3 and audio/narration-timing.json
(start and end of every line), which build.py puts into the page.

Needs ELEVENLABS_API_KEY (read from the environment, else ~/Projects/playmaker/.env)
and, for the bed, audio/instrumental.mp3.
Run: python3 build-narration.py
"""
import hashlib, json, os, subprocess, urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
AUDIO = ROOT / "audio"
CLIPS = AUDIO / "narr"
CLIPS.mkdir(parents=True, exist_ok=True)

LEAD = 3.2        # seconds of music before the first voice
GAP = 0.55        # pause between lines by the same speaker
GAP_SWITCH = 0.9  # pause when the speaker changes
TAIL = 0.6        # music after the last voice, before the song starts
MODEL = "eleven_multilingual_v2"


def api_key():
    k = os.environ.get("ELEVENLABS_API_KEY")
    if k:
        return k
    for line in (Path.home() / "Projects/playmaker/.env").read_text().splitlines():
        if line.startswith("ELEVENLABS_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"')
    raise SystemExit("ELEVENLABS_API_KEY not found")


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def render(line, voice):
    digest = hashlib.sha1(f"{MODEL}|{voice}|{line['text']}".encode()).hexdigest()[:10]
    path = CLIPS / f"{line['id']}-{digest}.mp3"
    if path.exists():
        return path
    body = {"text": line["text"], "model_id": MODEL,
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.35, "use_speaker_boost": True}}
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128",
        data=json.dumps(body).encode(),
        headers={"xi-api-key": api_key(), "Content-Type": "application/json", "Accept": "audio/mpeg"})
    path.write_bytes(urllib.request.urlopen(req, timeout=120).read())
    for old in CLIPS.glob(f"{line['id']}-*.mp3"):
        if old != path:
            old.unlink()
    print("rendered", path.name)
    return path


def main():
    spec = json.loads((ROOT / "narration.json").read_text())
    speakers = spec["speakers"]
    t, prev, timing, inputs = LEAD, None, [], []
    for line in spec["lines"]:
        clip = render(line, speakers[line["speaker"]]["voice"])
        if prev is not None:
            t += GAP if prev == line["speaker"] else GAP_SWITCH
        d = duration(clip)
        timing.append({"id": line["id"], "start": round(t, 3), "end": round(t + d, 3)})
        inputs.append((clip, t))
        t += d
        prev = line["speaker"]
    total = t + TAIL

    # Voices: delay each clip to its start time and sum them.
    args = ["ffmpeg", "-v", "error", "-y"]
    for clip, _ in inputs:
        args += ["-i", str(clip)]
    bed = AUDIO / "instrumental.mp3"
    has_bed = bed.exists()
    if has_bed:
        args += ["-i", str(bed)]
    parts = []
    for i, (_, start) in enumerate(inputs):
        ms = int(start * 1000)
        parts.append(f"[{i}:a]aresample=44100,aformat=channel_layouts=stereo,adelay={ms}|{ms}[v{i}]")
    mix = "".join(f"[v{i}]" for i in range(len(inputs)))
    parts.append(f"{mix}amix=inputs={len(inputs)}:normalize=0,apad,atrim=0:{total:.3f}[voice]")
    if has_bed:
        b = len(inputs)
        parts.append("[voice]asplit=2[voiceout][voicekey]")
        # The bed: start of the instrumental, faded in and out, ducked whenever a voice speaks.
        parts.append(f"[{b}:a]aresample=44100,aformat=channel_layouts=stereo,atrim=0:{total:.3f},volume=0.55,"
                     f"afade=t=in:d=1.5,afade=t=out:st={max(total - 1.2, 0):.3f}:d=1.2[bedraw]")
        parts.append("[bedraw][voicekey]sidechaincompress=threshold=0.015:ratio=10:attack=15:release=450:makeup=1[bedduck]")
        parts.append("[voiceout][bedduck]amix=inputs=2:normalize=0,loudnorm=I=-15:TP=-1.5:LRA=11,aresample=44100[out]")
    else:
        parts.append("[voice]anull[out]")
    args += ["-filter_complex", ";".join(parts), "-map", "[out]", "-c:a", "libmp3lame", "-b:a", "128k",
             str(AUDIO / "narration.mp3")]
    subprocess.run(args, check=True)
    (AUDIO / "narration-timing.json").write_text(json.dumps({"duration": round(total, 3), "lines": timing}, indent=1))
    print(f"narration.mp3: {total:.1f}s, {len(timing)} lines, bed={'yes' if has_bed else 'no'}")


if __name__ == "__main__":
    main()
