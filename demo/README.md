# Demo video

`assets/demo.mp4` and `assets/demo.gif` are generated headlessly from a
scripted tmux session. No screen recorder or display is needed.

- `record.py` starts an isolated tmux server (`tmux -L ardemo`) that loads this
  plugin. It spawns fake agents (`bin/fake-agent`, run as `claude`, `pi`, and
  `codex`), attaches one client in a pty, and plays the `TIMELINE` against it.
  The client's output, the captions, and the desktop notifications (captured
  by a `notify-send` stub) go to `demo.cast`.
- `render.py` replays `demo.cast` through a terminal emulator (pyte) and draws
  each frame with PIL. It then encodes `demo.mp4` with ffmpeg.

## Regenerate

Requires `tmux`, `fzf`, `git`, `ffmpeg`, the DejaVu and FreeFont fonts, and
Python with `pyte`, `fonttools`, and `Pillow`.

```sh
python3 -m venv /tmp/ardemo-venv && /tmp/ardemo-venv/bin/pip install pyte fonttools pillow
/tmp/ardemo-venv/bin/python demo/record.py
/tmp/ardemo-venv/bin/python demo/render.py            # or: --still 12,19 for PNG stills
cp demo/demo.mp4 assets/demo.mp4
ffmpeg -y -i demo/demo.mp4 -vf "fps=12,scale=1280:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];[b][p]paletteuse=dither=none:diff_mode=rectangle" assets/demo.gif
```

Agents stop when the driver bumps their control file, so the story is
deterministic. `record.py` prints a warning if a navigator jump didn't land on
the expected window.

`twemoji-radar.png` is the 📡 emoji from [Twemoji](https://github.com/jdecked/twemoji),
licensed CC-BY 4.0.
