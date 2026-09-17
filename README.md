# Garage Door — the making of a song

A one-page site that tells how the rap "Garage Door" was made: a remark on the
Wednesday Hootnet (Jess, Harold, Noel, George and Mike), lyrics by Claude,
music by Suno, and ten images written by four AIs and rendered by three.

- `lyrics.txt`: the lyrics as sent to Suno.
- `timed-lyrics.srt`: the timed lyric track from Suno's download of the song. The page uses it to scroll with the music, and to move the music when the reader scrolls, taps a line or taps a picture.
- `audio/garage-door.mp3`: the song (Suno download, Mike's Pro plan).
- `narration.json`: the narrated "How they did it" section. Each AI speaks its own part in its own ElevenLabs voice. `python3 build-narration.py` renders `audio/narration.mp3` over `audio/instrumental.mp3` (the song with the vocals removed by Demucs) and writes `audio/narration-timing.json`. Clips are cached in `audio/narr/`, so only changed lines cost ElevenLabs characters.
- The page offers two choices: play the song, or hear the team tell how they made it. The narration ends with a count-in and loops into the song. One audio element plays both tracks, so phones allow the song to start by itself.
- `credits.json`: for each image, the lyric section, the prompt writer, the image maker and the exact prompt.
- `template.html` + `build.py`: `python3 build.py` writes `index.html` (run `build-narration.py` first after changing the narration).
- `img/`: the rendered images (JPEG) and Suno's cover art.

- The page ends with a tip jar linking to
  `minds-aligned.org/support/?campaign=garage-door&ref=garage-door-song`. That page
  holds the prices and the Stripe keys; this one holds a link, so nothing here has
  to change when an amount does. `ref` is what credits this page in Stripe with
  whoever it brings in. See `SUPPORT.md` in eldrgeek/minds-aligned.

Live: https://garage-door-song.netlify.app

Authorship: Mike Wolf (producer) with Claude Opus 5 (Claude Code), 2026-09-16.
