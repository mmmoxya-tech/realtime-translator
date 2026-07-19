from __future__ import annotations

import sys
import threading
import time
from types import SimpleNamespace

from .audio import AudioCapture, AudioRingBuffer, default_sink
from .events import Event
from .punctuation import StreamingPunctuator
from .recognizer import StreamingRecognizer
from .translator import LocalTranslator
from .translation_queue import TranslationQueue
from .vad import UtteranceBoundary, VoiceActivityDetector


def emit(event: Event) -> None:
    print(event.encode(), flush=True)


def run(args) -> None:
    target = args.audio_target or default_sink()
    if not target:
        raise RuntimeError("找不到当前 PipeWire 输出设备")
    emit(Event.status("正在加载流式语音模型…"))
    recognizer = StreamingRecognizer(args.asr_model, args.asr_threads)
    recognizer.check()
    punctuator = StreamingPunctuator(args.punctuation_model)
    punctuator.check()
    translator = LocalTranslator(args.translation_model, args.translation_threads)
    translator.check()
    translator.warmup()
    vad = VoiceActivityDetector(mode=args.vad_mode)
    boundary = UtteranceBoundary(args.vad_silence, args.max_utterance)
    translations = TranslationQueue()
    def translate_loop():
        while True:
            update = translations.get()
            if update is None:
                return
            try:
                started_at = time.monotonic()
                translated = translator.translate(update.original)
                finished_at = time.monotonic()
                queue_ms = round((started_at - update.submitted_at) * 1000, 1)
                translation_ms = round((finished_at - started_at) * 1000, 1)
                end_to_end_ms = round((finished_at - update.audio_at) * 1000, 1)
                print(
                    f"translation metrics: utterance={update.utterance_id} "
                    f"revision={update.revision} queue_ms={queue_ms} "
                    f"translation_ms={translation_ms} "
                    f"end_to_end_ms={end_to_end_ms}",
                    file=sys.stderr,
                )
                emit(Event("translation", update.utterance_id, update.original,
                           translated, update.captured_at,
                           revision=update.revision,
                           queue_ms=queue_ms,
                           translation_ms=translation_ms,
                           asr_ms=update.asr_ms,
                           end_to_end_ms=end_to_end_ms))
            except Exception as exc:
                print(f"translation error: {exc}", file=sys.stderr)
                emit(Event("error", update.utterance_id, update.original,
                           captured_at=update.captured_at,
                           message="翻译暂时不可用",
                           revision=update.revision))

    worker = threading.Thread(target=translate_loop, daemon=True)
    worker.start()
    audio = AudioRingBuffer(16000, 3.0)
    capture = AudioCapture(target, audio, block_seconds=args.audio_block)
    capture.start()
    emit(Event.status(f"实时聆听 · ZIPFORMER · {target}"))
    next_device_check = time.monotonic() + 2.0

    def queue_translation(update) -> None:
        translations.put(update)

    utterance_id = 1
    revision = 0
    last_version = -1
    last_text = ""
    captured_at = 0.0
    try:
        while True:
            time.sleep(args.step)
            if not capture.alive:
                reason = capture.error or "PipeWire 音频捕获已停止"
                print(f"audio capture stopped: {reason}", file=sys.stderr)
                emit(Event.status("音频捕获中断，正在重新连接…"))
                capture.stop()
                time.sleep(0.5)
                reconnect_target = args.audio_target or default_sink()
                if not reconnect_target:
                    continue
                try:
                    capture = AudioCapture(
                        reconnect_target, audio,
                        block_seconds=args.audio_block)
                    capture.start()
                except RuntimeError as exc:
                    print(f"audio reconnect failed: {exc}", file=sys.stderr)
                    continue
                target = reconnect_target
                last_version = audio.latest_version
                emit(Event.status(f"已重新连接 · {target}"))
                next_device_check = time.monotonic() + 2.0
                continue
            if not args.audio_target and time.monotonic() >= next_device_check:
                next_device_check = time.monotonic() + 2.0
                current_default = default_sink()
                if current_default and current_default != target:
                    emit(Event.status(f"正在切换音频设备 · {current_default}"))
                    replacement = AudioCapture(
                        current_default, audio,
                        block_seconds=args.audio_block)
                    replacement.start()
                    capture.stop()
                    capture = replacement
                    target = current_default
                    last_version = audio.latest_version
                    emit(Event.status(f"实时聆听 · ZIPFORMER · {target}"))
                    continue
            blocks, newest_version, dropped = audio.blocks_after(last_version)
            if not blocks:
                continue
            if dropped:
                print(f"audio overrun: dropped {dropped} blocks", file=sys.stderr)
            last_version = newest_version
            audio_at = time.monotonic() - args.audio_block
            batch_has_speech = any(vad.is_speech(block) for block in blocks)
            speech_started, vad_endpoint = boundary.observe(
                batch_has_speech, audio_at, time.monotonic())
            if speech_started:
                captured_at = audio_at
                emit(Event("speech_start", utterance_id,
                           captured_at=captured_at))
            for block in blocks:
                recognizer.accept(block)
            text = recognizer.decode()
            decoded_at = time.monotonic()
            asr_ms = round((decoded_at - audio_at) * 1000, 1)
            if text and text != last_text:
                if not captured_at:
                    captured_at = time.monotonic() - args.audio_block
                update_at = time.monotonic() - args.audio_block
                display_text = punctuator.apply(text)
                revision += 1
                emit(Event("hypothesis", utterance_id, display_text,
                           captured_at=update_at, revision=revision,
                           asr_ms=asr_ms))
                if len(text.split()) >= 2:
                    queue_translation(SimpleNamespace(
                        type="hypothesis", utterance_id=utterance_id,
                        original=display_text, captured_at=update_at,
                        revision=revision, submitted_at=time.monotonic(),
                        audio_at=audio_at, asr_ms=asr_ms))
                last_text = text
            if recognizer.is_endpoint or vad_endpoint:
                if last_text:
                    final_text = punctuator.apply(last_text, final=True)
                    revision += 1
                    emit(Event("final", utterance_id, final_text,
                               captured_at=captured_at, revision=revision,
                               asr_ms=asr_ms))
                    queue_translation(SimpleNamespace(
                        type="final", utterance_id=utterance_id,
                        original=final_text, captured_at=captured_at,
                        revision=revision, submitted_at=time.monotonic(),
                        audio_at=audio_at, asr_ms=asr_ms))
                    utterance_id += 1
                recognizer.reset()
                revision = 0
                last_text = ""
                captured_at = 0.0
                boundary.reset()
    finally:
        capture.stop()
        translations.close()
        worker.join(timeout=2)
