# Garage Door — the making of a song

A one-page site that tells how the rap "Garage Door" was made: a remark on the
Wednesday Hootnet (Jess, Harold, Noel, George and Mike), lyrics by Claude,
music by Suno, and ten images written by four AIs and rendered by three.

- `lyrics.txt`: the lyrics as sent to Suno.
- `timed-lyrics.srt`: the timed lyric track from Suno's download of the song. The page uses it to scroll with the music, and to move the music when the reader scrolls, taps a line or taps a picture.
- `audio/garage-door.mp3`: the song (Suno download, Mike's Pro plan).
- `credits.json`: for each image, the lyric section, the prompt writer, the image maker and the exact prompt.
- `template.html` + `build.py`: `python3 build.py` writes `index.html`.
- `img/`: the rendered images (JPEG) and Suno's cover art.

Live: https://garage-door-song.netlify.app

Authorship: Mike Wolf (producer) with Claude Opus 5 (Claude Code), 2026-09-16.
