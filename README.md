# YouTube 视频下载、翻译与自动化压制工具

本项目是一个自动化的 YouTube 视频处理工具。它能够下载视频，提取音频，使用本地 AI 模型（Whisper）转录字幕，并调用 DeepSeek API 进行术语表增强的翻译，最后将双语字幕烧录进视频中。

## 1. 功能特性

- **视频下载**：利用 `yt-dlp` 下载最高质量的视频资源。
- **语音转文字**：集成 `faster-whisper` 在本地进行高效、高准确度的转录。
- **智能翻译**：对接 **DeepSeek API**，支持行业术语表（Glossary），确保专业词汇翻译准确且一致。
- **自动化压制**：使用 `FFmpeg` 自动合成字幕，支持多种显示模式。
- **项目管理**：支持以项目为单位组织视频任务，自动生成进度记录。

## 2. 环境准备

### 软件依赖
在运行本项目之前，请确保系统中已安装以下软件：

1.  **Python 3.10+**
2.  **FFmpeg**: 必须安装并在系统 PATH 中。用于提取音频和烧录字幕。
3.  **CUDA (可选)**: 如果需要 GPU 加速转录，请安装相应的 NVIDIA 驱动和 CUDA 环境。

### 安装依赖包
本项目推荐使用 [uv](https://github.com/astral-sh/uv) 管理依赖，以获得极速的安装体验：

```bash
# 安装 uv (如果尚未安装)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 同步项目依赖并创建虚拟环境
uv sync
```

## 3. 配置文件

在项目根目录下创建 `.env` 文件，并配置以下内容：

```env
# DeepSeek API 配置
DEEPSEEK_API_KEY=你的_DEEPSEEK_API_KEY
DEEPSEEK_API_BASE=https://api.deepseek.com

# 存储配置
OUTPUT_ROOT=output  # 项目数据和视频的输出根目录，默认为 output

# 模型配置
CHAT_MODEL=deepseek-chat
WHISPER_MODEL=base  # 可选: tiny, base, small, medium, large-v3
```

## 4. 使用说明

项目通过 `main.py` 进行命令行交互。

### 第一步：初始化项目
创建一个新项目并指定所属行业（用于生成行业术语表）：
```bash
python main.py init "强化学习课程" --industry "强化学习,人工智能"
```

### 第二步：添加视频
向项目中添加单个视频或整个播放列表链接：
```bash
python main.py add "强化学习课程" "https://www.youtube.com/watch?v=..."
```

### 第三步：开始执行
运行全自动处理流程（下载 -> 转录 -> 翻译 -> 压制）：
```bash
python main.py run "强化学习课程"
```

### 其他命令
- **查看项目列表**：`python main.py list`
- **更新术语表**：`python main.py update-glossary "项目名" --industry "新行业"`

## 5. 字幕压制模式 (`burn_mode`)
在项目的 `project_config.json` 中可以修改 `burn_mode`：
- `none`: 不执行压制。
- `original`: 仅压制原语字幕（位于底部）。
- `translated`: 仅压制翻译字幕（位于顶部）。
- `double`: 同时压制双语字幕。

## 6. 项目结构
- `/src`: 核心源代码。
- `/output`: (默认) 存储项目配置、视频素材、字幕文件及最终成品。
- `main.py`: 命令行入口。

## 版权说明
本项目采用 [MIT License](LICENSE) 开源协议。

