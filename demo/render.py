#!/usr/bin/env python3
"""Render demo.cast (from record.py) into demo.mp4 with pyte + PIL + ffmpeg.

Frames: a window-chrome frame around the terminal, a caption bar below it,
and desktop-notification toasts (from "n" events) sliding in at top right.
"""
import json
import os
import subprocess
import sys

import pyte
from pyte import graphics as g
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 20
W = 1920
FONT_SIZE = 19
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FALLBACK_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
MONO2 = "/usr/share/fonts/truetype/freefont/FreeMono.ttf"  # has ⎇ at cell width
MONO2_B = "/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf"
UI = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
UI_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
EMOJI = {"📡": os.path.join(HERE, "twemoji-radar.png")}

# Catppuccin Mocha
BG, FG = "#1e1e2e", "#cdd6f4"
PAGE = "#11111b"
ANSI = {
    "black": "#45475a", "red": "#f38ba8", "green": "#a6e3a1", "brown": "#f9e2af",
    "blue": "#89b4fa", "magenta": "#f5c2e7", "cyan": "#94e2d5", "white": "#bac2de",
    "brightblack": "#585b70", "brightred": "#f38ba8", "brightgreen": "#a6e3a1", "brightbrown": "#f9e2af",
    "brightblue": "#89b4fa", "brightmagenta": "#f5c2e7", "brightcyan": "#94e2d5", "brightwhite": "#a6adc8",
}
for i, name in enumerate(["black", "red", "green", "brown", "blue", "magenta", "cyan", "white"]):
    ANSI[g.FG_BG_256[i]] = ANSI[name]
    ANSI[g.FG_BG_256[i + 8]] = ANSI["bright" + name]

# pyte ignores SGR 2 (dim); carry it in the otherwise unused blink slot.
g.TEXT[2] = "+blink"


class Screen(pyte.Screen):
    def select_graphic_rendition(self, *attrs, **kw):
        if 22 in attrs:
            attrs = attrs + (25,)
        super().select_graphic_rendition(*attrs)


def color(c, default):
    if c == "default":
        return default
    if c in ANSI:
        return ANSI[c]
    return "#" + c


def mix(a, b, t):
    a, b = [tuple(int(x[i:i + 2], 16) for i in (1, 3, 5)) for x in (a, b)]
    return "#%02x%02x%02x" % tuple(round(p + (q - p) * t) for p, q in zip(a, b))


class Fonts:
    def __init__(self):
        self.mono = ImageFont.truetype(MONO, FONT_SIZE)
        self.mono_b = ImageFont.truetype(MONO_B, FONT_SIZE)
        self.fb = ImageFont.truetype(FALLBACK, FONT_SIZE)
        self.fb_b = ImageFont.truetype(FALLBACK_B, FONT_SIZE)
        self.cmap = TTFont(MONO).getBestCmap()
        self.cmap2 = TTFont(MONO2).getBestCmap()
        self.mono2 = ImageFont.truetype(MONO2, FONT_SIZE + 2)
        self.mono2_b = ImageFont.truetype(MONO2_B, FONT_SIZE + 2)
        self.cw = self.mono.getlength("M")
        asc, desc = self.mono.getmetrics()
        self.ch = asc + desc + 3
        self._fit = {}
        self.emoji = {k: Image.open(p).convert("RGBA") for k, p in EMOJI.items()}

    def fit(self, ch, bold, max_w):
        """Fallback font, shrunk so a proportional glyph fits its cells."""
        size = FONT_SIZE
        while size > 8:
            key = (bold, size)
            if key not in self._fit:
                self._fit[key] = ImageFont.truetype(FALLBACK_B if bold else FALLBACK, size)
            if self._fit[key].getlength(ch) <= max_w + 0.5:
                return self._fit[key]
            size -= 1
        return self._fit[(bold, size + 1)]

    def pick(self, ch, bold):
        if ord(ch[0]) in self.cmap:
            return self.mono_b if bold else self.mono
        if ord(ch[0]) in self.cmap2:
            return self.mono2_b if bold else self.mono2
        return self.fb_b if bold else self.fb


def draw_terminal(screen, fonts):
    cols, rows = screen.columns, screen.lines
    cw, ch = fonts.cw, fonts.ch
    img = Image.new("RGB", (round(cols * cw), rows * ch), BG)
    d = ImageDraw.Draw(img)
    for y in range(rows):
        line = screen.buffer[y]
        glyphs = []  # drawn after the row's backgrounds so overhangs aren't painted over
        x = 0
        while x < cols:
            c = line[x]
            fg, bg = color(c.fg, FG), color(c.bg, BG)
            if c.reverse:
                fg, bg = bg, fg
            if c.blink:  # dim
                fg = mix(fg, bg, 0.45)
            width = 2 if (x + 1 < cols and line[x + 1].data == "") and c.data not in ("", " ") else 1
            px, py = round(x * cw), y * ch
            if bg != BG:
                d.rectangle([px, py, round((x + width) * cw) - 1, py + ch - 1], fill=bg)
            data = c.data
            if data and data != " ":
                glyphs.append((x, width, px, py, data, fg, c))
            x += width
        for x, width, px, py, data, fg, c in glyphs:
            if data in fonts.emoji:
                size = ch - 2
                em = fonts.emoji[data].resize((size, size), Image.LANCZOS)
                img.paste(em, (px + round((2 * cw - size) / 2), py + 1), em)
            elif data[0] in "─│╭╮╰╯┌┐└┘├┤┬┴┼":
                draw_box(d, data[0], px, py, cw, ch, fg)
            else:
                font = fonts.pick(data, c.bold)
                off, dy = 0, 1
                if font in (fonts.fb, fonts.fb_b):
                    font = fonts.fit(data, c.bold, width * cw)
                    off = (width * cw - font.getlength(data)) / 2
                    dy += (FONT_SIZE - font.size) // 2
                d.text((px + off, py + dy), data, font=font, fill=fg)
            if c.underscore:
                d.line([px, py + ch - 2, px + width * cw, py + ch - 2], fill=fg)
    if not screen.cursor.hidden:
        cx, cy = screen.cursor.x, screen.cursor.y
        if 0 <= cx < cols and 0 <= cy < rows:
            d.rectangle([round(cx * cw), cy * ch, round((cx + 1) * cw) - 1, cy * ch + ch - 1], fill="#f5e0dc")
            c = screen.buffer[cy][cx]
            if c.data.strip():
                d.text((round(cx * cw), cy * ch + 1), c.data, font=fonts.pick(c.data, c.bold), fill=BG)
    return img


def draw_box(d, c, px, py, cw, ch, fg):
    # Draw box glyphs as lines so borders join seamlessly across cells.
    mx, my = px + cw / 2, py + ch / 2
    x0, x1, y0, y1 = px, px + cw, py, py + ch
    r = min(cw, ch) / 2
    segs = {
        "─": [(x0, my, x1, my)], "│": [(mx, y0, mx, y1)],
        "┌": [(mx, my, x1, my), (mx, my, mx, y1)], "┐": [(x0, my, mx, my), (mx, my, mx, y1)],
        "└": [(mx, y0, mx, my), (mx, my, x1, my)], "┘": [(mx, y0, mx, my), (x0, my, mx, my)],
        "├": [(mx, y0, mx, y1), (mx, my, x1, my)], "┤": [(mx, y0, mx, y1), (x0, my, mx, my)],
        "┬": [(x0, my, x1, my), (mx, my, mx, y1)], "┴": [(x0, my, x1, my), (mx, y0, mx, my)],
        "┼": [(x0, my, x1, my), (mx, y0, mx, y1)],
    }
    if c in segs:
        for s in segs[c]:
            d.line(s, fill=fg, width=1)
        return
    # rounded corners: short straight runs plus a quarter arc
    if c == "╭":
        d.line((mx + r, my, x1, my), fill=fg); d.line((mx, my + r, mx, y1), fill=fg)
        d.arc((mx, my, mx + 2 * r, my + 2 * r), 180, 270, fill=fg)
    elif c == "╮":
        d.line((x0, my, mx - r, my), fill=fg); d.line((mx, my + r, mx, y1), fill=fg)
        d.arc((mx - 2 * r, my, mx, my + 2 * r), 270, 360, fill=fg)
    elif c == "╰":
        d.line((mx + r, my, x1, my), fill=fg); d.line((mx, y0, mx, my - r), fill=fg)
        d.arc((mx, my - 2 * r, mx + 2 * r, my), 90, 180, fill=fg)
    elif c == "╯":
        d.line((x0, my, mx - r, my), fill=fg); d.line((mx, y0, mx, my - r), fill=fg)
        d.arc((mx - 2 * r, my - 2 * r, mx, my), 0, 90, fill=fg)


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


class Composer:
    def __init__(self, cols, rows):
        self.fonts = Fonts()
        self.ui = ImageFont.truetype(UI, 30)
        self.ui_b = ImageFont.truetype(UI_B, 30)
        self.small = ImageFont.truetype(UI, 20)
        self.small_b = ImageFont.truetype(UI_B, 21)
        self.tw, self.th = round(cols * self.fonts.cw), rows * self.fonts.ch
        self.bar = 38
        self.pad = 18
        self.win_w = self.tw + 2 * self.pad
        self.win_h = self.th + self.bar + self.pad
        self.wx = (W - self.win_w) // 2
        self.wy = 40
        base = Image.new("RGB", (W, (self.wy + self.win_h + 110) // 2 * 2), PAGE)
        d = ImageDraw.Draw(base)
        d.rounded_rectangle([self.wx, self.wy, self.wx + self.win_w, self.wy + self.win_h], 14, fill=BG,
                            outline="#313244", width=2)
        for i, col in enumerate(["#f38ba8", "#f9e2af", "#a6e3a1"]):
            cx, cy = self.wx + 24 + i * 24, self.wy + self.bar // 2 + 2
            d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=col)
        title = "tmux — agent-radar"
        d.text((self.wx + self.win_w / 2 - self.small.getlength(title) / 2, self.wy + 9), title,
               font=self.small, fill="#6c7086")
        self.base = base
        global H
        H = (self.wy + self.win_h + 110) // 2 * 2
        self.cap_y = self.wy + self.win_h + 55

    def frame(self, term, caption, cap_t, toasts, t):
        img = self.base.copy()
        img.paste(term, (self.wx + self.pad, self.wy + self.bar))
        d = ImageDraw.Draw(img, "RGBA")
        if caption:
            a = ease(cap_t / 0.35)
            w = self.ui.getlength(caption)
            y = self.cap_y - 20 + round((1 - a) * 12)
            d.text((W / 2 - w / 2, y), caption, font=self.ui, fill=(205, 214, 244, round(255 * a)))
        for i, (t0, title, body) in enumerate(toasts):
            self.toast(img, d, t - t0, title, body, i)
        return img

    def toast(self, img, d, age, title, body, slot):
        life = 4.5
        if age < 0 or age > life:
            return
        slide = ease(age / 0.35) if age < life - 0.35 else ease((life - age) / 0.35)
        tw, th = 430, 88
        x = self.wx + self.win_w - 20 - tw + round((1 - slide) * (tw + 40))
        y = self.wy + self.bar + 16 + slot * (th + 12)
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ld.rounded_rectangle([x + 4, y + 6, x + tw + 4, y + th + 6], 14, fill=(0, 0, 0, 90))
        ld.rounded_rectangle([x, y, x + tw, y + th], 14, fill="#313244", outline="#45475a", width=2)
        em = self.fonts.emoji["📡"].resize((44, 44), Image.LANCZOS)
        layer.paste(em, (x + 18, y + 22), em)
        ld.text((x + 78, y + 18), title, font=self.small_b, fill="#cdd6f4")
        ld.text((x + 78, y + 50), body, font=self.small, fill="#a6adc8")
        mask = layer.getchannel("A")
        img.paste(layer, (0, 0), mask)


def main():
    src = os.path.join(HERE, "demo.cast")
    out = os.path.join(HERE, "demo.mp4")
    lines = open(src).read().splitlines()
    header = json.loads(lines[0])
    events = [json.loads(l) for l in lines[1:]]
    screen = Screen(header["width"], header["height"])
    stream = pyte.ByteStream(screen)
    comp = Composer(header["width"], header["height"])
    end = events[-1][0]
    # render.py [--still t1,t2,...]: write PNG stills instead of the video
    stills = [float(x) for x in sys.argv[2].split(",")] if sys.argv[1:2] == ["--still"] else None
    start = 0.0

    ff = None if stills else subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                           "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out],
                          stdin=subprocess.PIPE)
    ei = 0
    caption, cap_at = None, 0.0
    toasts = []
    term = None
    dirty = True
    n = int((end - start) * FPS)
    for f in range(n):
        t = start + f / FPS
        while ei < len(events) and events[ei][0] <= t:
            ts, kind, data = events[ei]
            if kind == "o":
                stream.feed(data.encode("utf-8"))
                dirty = True
            elif kind == "c":
                caption, cap_at = data, ts
            elif kind == "n":
                title, _, body = data.partition("\t")
                toasts = [x for x in toasts if t - x[0] < 4.5]
                toasts.append((ts, title, body))
            ei += 1
        if stills is not None and not any(abs(t - s) < 0.5 / FPS for s in stills):
            continue
        if dirty or term is None:
            term = draw_terminal(screen, comp.fonts)
            dirty = False
        if stills is not None:
            if any(abs(t - s) < 0.5 / FPS for s in stills):
                comp.frame(term, caption, t - cap_at, toasts, t).save(os.path.join(HERE, f"still-{t:05.1f}.png"))
            continue
        img = comp.frame(term, caption, t - cap_at, toasts, t)
        ff.stdin.write(img.tobytes())
        if f % 100 == 0:
            print(f"frame {f}/{n}", file=sys.stderr)
    if ff:
        ff.stdin.close()
        ff.wait()
    print(out)


if __name__ == "__main__":
    main()
