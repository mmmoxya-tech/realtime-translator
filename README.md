# Realtime Translator

版本：1.0.0（最终稳定版）

面向 Linux/Wayland 的完全本地、手机系统风格英译中实时翻译。它捕获当前扬声器或耳机正在播放的声音，用 Zipformer Transducer 真流式识别，再交给专用 OPUS-MT 模型低延迟翻译。

## 数据流

```text
PipeWire 100ms 音频块 → sherpa-onnx Zipformer 状态化流式识别
         → INT8 在线标点/大小写恢复 → 单词级增量字幕
         → 异步 CTranslate2 OPUS-MT 翻译
         → GTK4 layer-shell 双语悬浮卡片
```

识别和翻译不会阻塞音频捕获。音频和文本均不发送到云端。悬浮层显示在线标点处理后的当前识别和译文，并通过字幕 ID 原地更新同一句话。

## 安装

系统依赖：PipeWire、WirePlumber、GTK4、gtk4-layer-shell、python-gobject 和 python-cairo。翻译完全本地运行，不需要 Ollama 或网络。

```bash
cd ~/realtime-translator
./scripts/install-models.sh   # 源码仓库未附带模型时
./install.sh
```

模型通过独立的 GitHub Release 资产分发。配置 `origin` 为 GitHub 仓库后，
`install-models.sh` 会自动推导 `models-1.0.0` Release 地址；也可以把完整资产
URL 作为第一个参数传入。

## 启动

```bash
translate
```

默认使用 INT8 英语 Zipformer 流式模型，CPU 即可实时运行。程序会跟随
PipeWire 默认输出设备，并在捕获中断时自动重连。常用参数：

```bash
translate --step 0.05
translate --vad-silence 0.8 --max-utterance 15
translate --audio-target NODE_NAME
translate --overlay-width 960 --overlay-bottom 90
translate --overlay-timeout 6 --overlay-scale 1.15
```

指定 `--audio-target` 后将固定使用该设备，不再自动跟随系统默认设备。
运行日志包含 ASR、翻译排队、翻译执行和端到端延迟指标，以及音频缓冲
溢出警告。

环境诊断：

```bash
translate --diagnose
```

## 检查

```bash
.venv/bin/python -m unittest discover -s tests -v
python3 -m py_compile main.py overlay.py rttranslate/*.py
bash -n run.sh install.sh translate
```

## 运行模型

- 英语流式识别：sherpa-onnx Zipformer Transducer INT8
- 英语在线标点：sherpa-onnx CNN-BiLSTM INT8
- 英译中：OPUS-MT / CTranslate2 INT8

模型、音频和字幕均保留在本机。默认模型已经随项目封装，正常使用不需要联网。
安装时会使用 `MODEL_SHA256SUMS` 校验随项目提供的模型，避免不完整或损坏的
模型在运行时产生难以定位的错误。

## 开发检查

```bash
.venv/bin/python -m unittest discover -s tests -v
python3 -m py_compile main.py overlay.py rttranslate/*.py
bash -n run.sh install.sh translate
sha256sum --check MODEL_SHA256SUMS
.venv/bin/python benchmarks/run_translation.py
```

项目源码采用 Apache License 2.0。模型不因与项目一同分发而被重新许可，
具体来源和许可说明参见 `NOTICE` 以及模型资产内保留的上游文件。

## 发布模型资产

```bash
./scripts/package-models.sh
```

将 `dist/` 中生成的 `.tar.zst` 和 `.sha256` 文件上传至名为
`models-1.0.0` 的 GitHub Release。模型二进制被 `.gitignore` 排除，不应直接
提交到普通 Git 历史中。
