# 🎬 yt-translate

> YouTube 视频自动下载 · 转录 · 翻译 · 字幕压制 一条龙工具

```
📥 yt-dlp 下载  ➜  🎙️ Whisper 转录  ➜  🌐 GLM 翻译  ➜  🔥 FFmpeg 压制成片
```

以「项目」为单位批量管理视频任务：指定行业后自动生成术语表，保证专业词汇翻译一致，最终产出烧录双语字幕的成品视频。

## ✨ 功能特性

- 📥 **视频下载** — 基于 `yt-dlp`，自动抓取最高画质，支持单个视频与播放列表
- 🎙️ **本地转录** — `faster-whisper` 离线生成 SRT 字幕，无需上传音频，自动断句切分
- 🌐 **术语增强翻译** — 对接 **智谱 GLM API**（OpenAI 兼容接口），按行业术语表（Glossary）翻译，术语统一、语境地道
- 🔥 **自动压制** — FFmpeg 烧录字幕，支持原语 / 翻译 / 双语三种显示模式
- 📁 **项目管理** — 项目级配置与进度记录，**支持断点续跑**（已完成步骤自动跳过）
- 📊 **进度总览** — 一条命令查看所有项目的处理进度

## 🧰 环境准备

| 依赖 | 说明 |
|---|---|
| Python 3.10+ | 运行环境 |
| [FFmpeg](https://ffmpeg.org) | 必须安装并在 PATH 中，用于提取音频与压制字幕 |
| [uv](https://github.com/astral-sh/uv)（推荐） | 依赖管理，安装体验极佳 |

```bash
# 安装 uv（如果尚未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 同步依赖并创建虚拟环境
uv sync
```

## ⚙️ 配置

在项目根目录创建 `.env` 文件（已在 `.gitignore` 中，**请勿提交**）：

```env
# 智谱 GLM API 配置（Key 获取：https://open.bigmodel.cn）
GLM_API_KEY=你的_GLM_API_KEY
GLM_API_BASE=https://open.bigmodel.cn/api/paas/v4

# 存储配置
OUTPUT_ROOT=output   # 项目数据与视频的输出根目录，默认为 output

# 模型配置
CHAT_MODEL=glm-5.3-flash   # 翻译所用模型
WHISPER_MODEL=base         # 可选: tiny, base, small, medium, large-v3
```

## 🚀 使用说明

所有命令通过 `main.py` 执行，加 `--debug` 可查看详细 AI 调用日志。

### 1️⃣ 初始化项目

```bash
python main.py init "强化学习课程" -i "强化学习,人工智能"
```

`-i/--industry` 指定逗号分隔的行业领域，AI 将自动生成对应术语表（每行业 60 个术语）。

### 2️⃣ 添加视频

```bash
python main.py add "强化学习课程" "https://www.youtube.com/watch?v=..."
```

支持播放列表链接，自动去重并分配视频编号。

### 3️⃣ 一键执行

```bash
python main.py run "强化学习课程"
```

全自动流水线：下载 → 转录 → 翻译 → 压制。中断后重新执行会跳过已完成的步骤。

### 4️⃣ 其他命令

```bash
python main.py list                              # 📋 查看所有项目及进度
python main.py glossary "项目名" -i "新行业"       # 📖 追加生成术语表
python main.py --debug run "项目名"               # 🐛 调试模式
```

## 🎨 字幕压制模式

在项目的 `project_config.json` 中修改 `settings.burn_mode`：

| 模式 | 效果 |
|---|---|
| `none` | 不压制，仅生成字幕文件 |
| `original` | 仅原语字幕（底部，白色） |
| `translated` | 仅翻译字幕（顶部，黄色） |
| `double`（默认） | 双语字幕同时烧录 |

## 📂 项目结构

```text
.
├── src/                # 核心逻辑 (AI, 视频, YouTube 处理)
├── output/             # 默认数据存储目录
│   └── [项目名]/
│       ├── project_config.json   # 项目配置与进度
│       ├── glossary.json         # 行业术语表
│       └── videos/v001/          # 视频素材 (raw.mp4) 与成品 (output.mp4)
├── main.py             # 命令行入口
├── cli.py              # 命令行界面定义
└── .env                # 敏感配置 (API Key)，不入库
```

## ⚠️ 注意事项

- 🔑 `.env` 含 API Key，已被 `.gitignore` 排除，请勿手动提交或分享
- 🐢 默认 CPU 转录（int8），长视频较慢，可更换 `WHISPER_MODEL` 或接入 GPU
- 🌍 下载 YouTube 需可访问的网络环境
- 📺 仅供个人学习与研究使用，请遵守视频内容的版权与平台条款

## 📄 版权说明

本项目采用 [MIT License](LICENSE) 开源协议。
