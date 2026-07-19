#!/usr/bin/env python3
import argparse
import html
import json
import sys
import time

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gio, GLib, Gtk, Gtk4LayerShell, Pango


CSS = b"""
window { background: transparent; }
.card {
        background-color: rgba(18,19,23,.36);
        background-image: linear-gradient(to bottom,
                          rgba(255,255,255,.16),
                          rgba(255,255,255,.035));
        border: 1px solid rgba(255,255,255,.28);
        border-radius: 26px;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.18),
                    0 10px 32px rgba(0,0,0,.30);
        padding: 12px 24px;
}
.translation {
        color: rgba(255,255,255,.98);
        font-family: "Noto Sans CJK SC", "Noto Sans", sans-serif;
        font-weight: 500;
}
.original {
        color: rgba(235,238,245,.66);
        font-family: "Noto Sans", "Noto Sans CJK SC", sans-serif;
        font-weight: 400;
}
.error { color: #ffb4ab; }
"""


class Overlay(Gtk.Application):
    def __init__(self, args):
        super().__init__(application_id="dev.moxya.RealtimeTranslator",
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.args = args
        self.buffer = b""
        self.current_id = 0
        self.current_revision = 0
        self.translated_id = 0
        self.last_update = 0.0
        self.opacity = 1.0
        self.target_opacity = 1.0

    def text_size(self, base):
        return str(round(base * self.args.overlay_scale))

    def do_activate(self):
        window = Gtk.ApplicationWindow(application=self)
        window.set_default_size(self.args.overlay_width, 1)
        Gtk4LayerShell.init_for_window(window)
        Gtk4LayerShell.set_namespace(window, "realtime-translator")
        Gtk4LayerShell.set_layer(window, Gtk4LayerShell.Layer.OVERLAY)
        Gtk4LayerShell.set_anchor(window, Gtk4LayerShell.Edge.BOTTOM, True)
        Gtk4LayerShell.set_margin(
            window, Gtk4LayerShell.Edge.BOTTOM, self.args.overlay_bottom)
        Gtk4LayerShell.set_keyboard_mode(window, Gtk4LayerShell.KeyboardMode.NONE)
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            window.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card.add_css_class("card")
        card.set_size_request(self.args.overlay_width, -1)
        self.card = card
        self.translation = Gtk.Label(label="正在启动…")
        self.translation.add_css_class("translation")
        self.translation.set_wrap(True)
        self.translation.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.translation.set_lines(2)
        self.translation.set_hexpand(True)
        self.translation.set_justify(Gtk.Justification.CENTER)
        self.original = Gtk.Label()
        self.original.add_css_class("original")
        self.original.set_wrap(True)
        self.original.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.original.set_lines(1)
        self.original.set_hexpand(True)
        self.original.set_justify(Gtk.Justification.CENTER)
        card.append(self.translation)
        card.append(self.original)
        window.set_child(card)
        window.present()
        self.window = window
        GLib.io_add_watch(
            sys.stdin.fileno(),
            GLib.IOCondition.IN | GLib.IOCondition.HUP | GLib.IOCondition.ERR,
            self.on_input,
        )
        GLib.timeout_add(50, self.tick)

    def reveal(self):
        self.card.set_visible(True)
        self.target_opacity = 1.0

    def on_input(self, fd, condition):
        if condition & (GLib.IOCondition.HUP | GLib.IOCondition.ERR):
            self.quit()
            return GLib.SOURCE_REMOVE
        chunk = sys.stdin.buffer.read1(8192)
        if not chunk:
            self.quit()
            return GLib.SOURCE_REMOVE
        self.buffer += chunk
        while b"\n" in self.buffer:
            raw, self.buffer = self.buffer.split(b"\n", 1)
            try:
                self.show_event(json.loads(raw))
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        return GLib.SOURCE_CONTINUE

    def show_event(self, event):
        kind = event.get("type")
        self.last_update = time.monotonic()
        self.reveal()
        if kind != "error":
            self.translation.remove_css_class("error")
        if kind == "status":
            self.translation.set_markup(
                f'<span size="{self.text_size(13500)}" alpha="70%">'
                f'{html.escape(event.get("message", ""))}</span>')
            self.original.set_visible(False)
            return
        utterance_id = int(event.get("utterance_id", 0))
        if utterance_id < self.current_id:
            return
        revision = int(event.get("revision", 0))
        if utterance_id > self.current_id:
            self.current_revision = 0
        if utterance_id == self.current_id and revision < self.current_revision:
            return
        self.current_id = utterance_id
        self.current_revision = revision
        original = event.get("original", "")
        if original:
            self.original.set_visible(True)
            self.original.set_markup(
                f'<span size="{self.text_size(13500)}">{html.escape(original)}</span>')
        if kind == "speech_start":
            self.translation.set_markup(
                f'<span size="{self.text_size(14500)}" alpha="65%">正在识别…</span>')
            self.original.set_visible(False)
        elif kind == "hypothesis":
            self.original.set_visible(True)
            self.original.set_markup(
                f'<span size="{self.text_size(14000)}">'
                f'{html.escape(event.get("original", ""))}</span>')
            if self.translated_id != utterance_id:
                self.translation.set_markup(
                    f'<span size="{self.text_size(14500)}" '
                    'alpha="65%">正在识别…</span>')
        elif kind == "final":
            if self.translated_id != utterance_id:
                self.translation.set_markup(
                    f'<span size="{self.text_size(14500)}">正在翻译…</span>')
        elif kind == "translation":
            self.translated_id = utterance_id
            self.translation.set_markup(
                f'<span size="{self.text_size(18000)}">'
                f'{html.escape(event.get("translation", ""))}</span>')
        elif kind == "error":
            self.translation.set_markup(
                f'<span size="{self.text_size(14500)}">翻译暂时不可用</span>')
            self.translation.add_css_class("error")

    def tick(self):
        if (self.last_update and
                time.monotonic() - self.last_update > self.args.overlay_timeout):
            self.target_opacity = 0.0
        if self.opacity < self.target_opacity:
            self.opacity = min(self.target_opacity, self.opacity + 0.18)
        elif self.opacity > self.target_opacity:
            self.opacity = max(self.target_opacity, self.opacity - 0.12)
        self.card.set_opacity(self.opacity)
        if self.opacity == 0.0:
            self.card.set_visible(False)
            self.last_update = 0.0
        return GLib.SOURCE_CONTINUE


def parse_args():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--overlay-width", type=int, default=840)
    parser.add_argument("--overlay-bottom", type=int, default=72)
    parser.add_argument("--overlay-timeout", type=float, default=4.0)
    parser.add_argument("--overlay-scale", type=float, default=1.0)
    return parser.parse_known_args()[0]


if __name__ == "__main__":
    raise SystemExit(Overlay(parse_args()).run(sys.argv[:1]))
