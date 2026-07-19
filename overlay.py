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

from rttranslate.display import LatestUpdateGate


CSS = b"""
window.translator-window,
window.translator-window.background,
#realtime-translator-window {
        background-color: transparent;
        background-image: none;
        border-color: transparent;
        border-radius: 0;
        box-shadow: none;
}
.translator-surface {
        background-color: transparent;
        background-image: none;
        border-color: transparent;
        border-radius: 0;
        box-shadow: none;
        padding: 8px 16px;
}
.translator-surface.glass {
        background-color: rgba(20,24,32,.20);
        background-image: linear-gradient(to bottom,
                          rgba(255,255,255,.13),
                          rgba(255,255,255,.025));
        border: 1px solid rgba(255,255,255,.24);
        border-radius: 20px;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.14),
                    0 8px 24px rgba(0,0,0,.18);
        padding: 10px 22px;
}
.translation {
        color: rgba(255,255,255,.98);
        font-family: "Noto Sans CJK SC", "Noto Sans", sans-serif;
        font-weight: 500;
        text-shadow: 0 2px 5px rgba(0,0,0,.95),
                     0 0 2px rgba(0,0,0,1);
}
.original {
        color: rgba(242,244,248,.82);
        font-family: "Noto Sans", "Noto Sans CJK SC", sans-serif;
        font-weight: 400;
        text-shadow: 0 2px 4px rgba(0,0,0,.95),
                     0 0 2px rgba(0,0,0,1);
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
        self.label_markup = {}
        self.text_animations = {}
        self.held = False
        self.translation_gate = LatestUpdateGate(
            args.overlay_update_interval)
        hypothesis_interval = (0 if args.overlay_update_interval == 0 else
                               min(0.3, args.overlay_update_interval / 3))
        self.hypothesis_gate = LatestUpdateGate(hypothesis_interval)

    def text_size(self, base):
        return str(round(base * self.args.overlay_scale))

    def set_animated_markup(self, label, markup, strength=0.35):
        """Replace label text once and ease it in without hiding old content."""
        if self.label_markup.get(label) == markup:
            return
        self.label_markup[label] = markup
        label.set_markup(markup)
        duration = self.args.overlay_animation_ms / 1000
        if duration <= 0:
            label.set_opacity(1.0)
            self.text_animations.pop(label, None)
            return
        label.set_opacity(1.0 - strength)
        self.text_animations[label] = (time.monotonic(), duration, strength)

    def do_activate(self):
        if not self.held:
            self.hold()
            self.held = True
        window = Gtk.ApplicationWindow(application=self)
        window.set_name("realtime-translator-window")
        window.add_css_class("translator-window")
        window.set_default_size(self.args.overlay_width, 1)
        Gtk4LayerShell.init_for_window(window)
        namespace = ("realtime-translator-glass"
                     if self.args.overlay_style == "glass"
                     else "realtime-translator")
        Gtk4LayerShell.set_namespace(window, namespace)
        Gtk4LayerShell.set_layer(window, Gtk4LayerShell.Layer.OVERLAY)
        Gtk4LayerShell.set_anchor(window, Gtk4LayerShell.Edge.BOTTOM, True)
        Gtk4LayerShell.set_margin(
            window, Gtk4LayerShell.Edge.BOTTOM, self.args.overlay_bottom)
        Gtk4LayerShell.set_keyboard_mode(window, Gtk4LayerShell.KeyboardMode.NONE)
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            window.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card.add_css_class("translator-surface")
        if self.args.overlay_style == "glass":
            card.add_css_class("glass")
        card.set_size_request(self.args.overlay_width, -1)
        self.card = card
        self.translation = Gtk.Label(label="正在启动…")
        self.translation.add_css_class("translation")
        self.translation.set_wrap(False)
        ellipsize = (Pango.EllipsizeMode.START
                     if self.args.overlay_long_text == "latest"
                     else Pango.EllipsizeMode.END)
        self.translation.set_ellipsize(ellipsize)
        self.translation.set_lines(1)
        self.translation.set_hexpand(True)
        self.translation.set_justify(Gtk.Justification.CENTER)
        self.original = Gtk.Label()
        self.original.add_css_class("original")
        self.original.set_wrap(False)
        self.original.set_ellipsize(ellipsize)
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
        if not self.window.get_visible():
            self.window.present()
        self.target_opacity = 1.0

    def on_input(self, fd, condition):
        if condition & (GLib.IOCondition.HUP | GLib.IOCondition.ERR):
            if self.held:
                self.release()
                self.held = False
            self.quit()
            return GLib.SOURCE_REMOVE
        chunk = sys.stdin.buffer.read1(8192)
        if not chunk:
            if self.held:
                self.release()
                self.held = False
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
            self.set_animated_markup(self.translation,
                f'<span size="{self.text_size(13500)}" alpha="70%">'
                f'{html.escape(event.get("message", ""))}</span>', 0.25)
            self.original.set_visible(False)
            return
        utterance_id = int(event.get("utterance_id", 0))
        if utterance_id < self.current_id:
            return
        revision = int(event.get("revision", 0))
        if utterance_id > self.current_id:
            self.current_revision = 0
            self.translation_gate.discard_before(utterance_id)
            self.hypothesis_gate.discard_before(utterance_id)
        if utterance_id == self.current_id and revision < self.current_revision:
            return
        self.current_id = utterance_id
        self.current_revision = revision
        now = time.monotonic()
        if kind == "translation":
            ready = self.translation_gate.submit(event, now)
            if ready is not None:
                self.show_translation(ready)
            return
        if kind == "hypothesis":
            ready = self.hypothesis_gate.submit(event, now)
            if ready is not None:
                self.show_hypothesis(ready)
            return
        original = event.get("original", "")
        if original:
            self.original.set_visible(True)
            self.set_animated_markup(
                self.original,
                f'<span size="{self.text_size(13500)}">{html.escape(original)}</span>',
                0.18)
        if kind == "speech_start":
            self.set_animated_markup(
                self.translation,
                f'<span size="{self.text_size(14500)}" alpha="65%">正在识别…</span>',
                0.25)
            self.original.set_visible(False)
        elif kind == "final":
            if self.translated_id != utterance_id:
                self.set_animated_markup(
                    self.translation,
                    f'<span size="{self.text_size(14500)}">正在翻译…</span>', 0.25)
        elif kind == "error":
            self.set_animated_markup(
                self.translation,
                f'<span size="{self.text_size(14500)}">翻译暂时不可用</span>', 0.3)
            self.translation.add_css_class("error")

    def show_hypothesis(self, event):
        utterance_id = int(event.get("utterance_id", 0))
        revision = int(event.get("revision", 0))
        if (utterance_id < self.current_id or
                (utterance_id == self.current_id and
                 revision < self.current_revision)):
            return
        self.original.set_visible(True)
        self.set_animated_markup(
            self.original,
            f'<span size="{self.text_size(14000)}">'
            f'{html.escape(event.get("original", ""))}</span>', 0.08)
        if self.translated_id != utterance_id:
            self.set_animated_markup(
                self.translation,
                f'<span size="{self.text_size(14500)}" '
                'alpha="65%">正在识别…</span>', 0.15)

    def show_translation(self, event):
        utterance_id = int(event.get("utterance_id", 0))
        revision = int(event.get("revision", 0))
        if (utterance_id < self.current_id or
                (utterance_id == self.current_id and
                 revision < self.current_revision)):
            return
        self.translated_id = utterance_id
        original = event.get("original", "")
        if original:
            self.original.set_visible(True)
            self.set_animated_markup(
                self.original,
                f'<span size="{self.text_size(13500)}">'
                f'{html.escape(original)}</span>', 0.08)
        self.set_animated_markup(
            self.translation,
            f'<span size="{self.text_size(18000)}">'
            f'{html.escape(event.get("translation", ""))}</span>', 0.32)

    def tick(self):
        now = time.monotonic()
        pending_translation = self.translation_gate.pop_due(now)
        if pending_translation is not None:
            self.show_translation(pending_translation)
        pending_hypothesis = self.hypothesis_gate.pop_due(now)
        if pending_hypothesis is not None:
            self.show_hypothesis(pending_hypothesis)
        for label, (started_at, duration, strength) in list(
                self.text_animations.items()):
            progress = min(1.0, (now - started_at) / duration)
            eased = 1.0 - (1.0 - progress) ** 3
            label.set_opacity(1.0 - strength * (1.0 - eased))
            if progress >= 1.0:
                self.text_animations.pop(label, None)
        if (self.last_update and
                now - self.last_update > self.args.overlay_timeout):
            self.target_opacity = 0.0
        if self.opacity < self.target_opacity:
            self.opacity = min(self.target_opacity, self.opacity + 0.18)
        elif self.opacity > self.target_opacity:
            self.opacity = max(self.target_opacity, self.opacity - 0.12)
        self.card.set_opacity(self.opacity)
        if self.opacity == 0.0:
            self.window.set_visible(False)
            self.last_update = 0.0
        return GLib.SOURCE_CONTINUE


def parse_args():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--overlay-width", type=int, default=1120)
    parser.add_argument("--overlay-bottom", type=int, default=72)
    parser.add_argument("--overlay-timeout", type=float, default=4.0)
    parser.add_argument("--overlay-scale", type=float, default=1.0)
    parser.add_argument("--overlay-animation-ms", type=int, default=180)
    parser.add_argument("--overlay-long-text", choices=("latest", "beginning"),
                        default="latest")
    parser.add_argument("--overlay-style", choices=("glass", "clear"),
                        default="glass")
    parser.add_argument("--overlay-update-interval", type=float, default=0.9)
    return parser.parse_known_args()[0]


if __name__ == "__main__":
    raise SystemExit(Overlay(parse_args()).run(sys.argv[:1]))
