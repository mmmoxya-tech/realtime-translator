#!/usr/bin/env python3
import argparse
import sys

from rttranslate.engine import run
from rttranslate.diagnostics import report


def main():
    parser = argparse.ArgumentParser(description="实时系统音频翻译")
    parser.add_argument("--asr-model",
                        default="models/sherpa-onnx-streaming-zipformer-en-2023-06-21")
    parser.add_argument("--asr-threads", type=int, default=4)
    parser.add_argument("--punctuation-model",
                        default="models/sherpa-onnx-online-punct-en-2024-08-06")
    parser.add_argument("--translation-model",
                        default="models/opus-mt-en-zh-ct2")
    parser.add_argument("--translation-threads", type=int, default=6)
    parser.add_argument("--diagnose", action="store_true")
    parser.add_argument("--audio-target")
    parser.add_argument("--audio-block", type=float, default=0.1)
    parser.add_argument("--step", type=float, default=0.05)
    parser.add_argument("--vad-mode", type=int, choices=range(4), default=2)
    parser.add_argument("--vad-silence", type=float, default=0.8,
                        help="连续静音多少秒后提交当前句")
    parser.add_argument("--max-utterance", type=float, default=15.0,
                        help="单句最长秒数，超过后强制切分")
    parser.add_argument("--overlay-width", type=int, default=840,
                        help="字幕卡片宽度")
    parser.add_argument("--overlay-bottom", type=int, default=72,
                        help="字幕卡片距屏幕底部像素")
    parser.add_argument("--overlay-timeout", type=float, default=4.0,
                        help="无新字幕多少秒后隐藏")
    parser.add_argument("--overlay-scale", type=float, default=1.0,
                        help="字幕字号缩放比例")
    args = parser.parse_args()
    if args.diagnose:
        raise SystemExit(report())
    if (args.audio_block <= 0 or args.step <= 0 or
            args.vad_silence <= 0 or args.max_utterance <= 0):
        parser.error("音频块、处理周期和断句时间必须大于零")
    if args.translation_threads < 1 or args.asr_threads < 1:
        parser.error("模型线程数必须大于零")
    if args.overlay_width < 320 or args.overlay_bottom < 0:
        parser.error("字幕宽度至少为 320，底部间距不能为负数")
    if args.overlay_timeout <= 0 or not 0.5 <= args.overlay_scale <= 2.5:
        parser.error("字幕隐藏时间必须大于零，字号缩放范围为 0.5 到 2.5")
    run(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except RuntimeError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        raise SystemExit(1)
