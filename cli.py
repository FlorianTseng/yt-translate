import logging
import typer
from typing import Optional
from tqdm import tqdm
from src.project_manager import ProjectManager
from src.youtube_service import YouTubeService
from src.ai_service import AIService
from src.video_service import VideoService

app = typer.Typer(help="YouTube 视频下载与翻译工具命令行界面", add_completion=False)
logger = logging.getLogger("CLI")

# 全局状态，用于存储调试模式
state = {"debug": False}


def setup_logging(debug: bool):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    if not debug:
        logging.getLogger("faster_whisper").setLevel(logging.WARNING)
        logging.getLogger("openai").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)


@app.callback()
def main(
    debug: bool = typer.Option(False, "--debug", help="启用调试日志"),
):
    """
    YouTube 视频下载与翻译工具命令行界面
    """
    state["debug"] = debug
    setup_logging(debug)


@app.command()
def init(
    name: str = typer.Argument(..., help="项目名称"),
    industry: str = typer.Option(
        "", "--industry", "-i", help="以逗号分隔的行业领域（用于生成术语表）"
    ),
):
    """
    初始化一个新项目
    """
    pm = ProjectManager()
    industries = [i.strip() for i in industry.split(",")] if industry else []
    project = pm.get_project(name)
    if project.exists():
        logger.info(f"项目 {name} 已存在。")
        return

    logger.info(f"正在初始化项目 {name}，所属行业：{industries}...")
    project.init_project(industries)

    ai = AIService()
    glossary = ai.generate_glossary(industries)
    project.save_glossary(glossary)
    logger.info(f"项目初始化完成。AI 自动生成了 {len(glossary)} 个术语。")


@app.command()
def add(
    name: str = typer.Argument(..., help="项目名称"),
    url: str = typer.Argument(..., help="YouTube 视频或播放列表链接"),
):
    """
    向项目中添加视频链接
    """
    pm = ProjectManager()
    project = pm.get_project(name)
    if not project.exists():
        logger.error(f"找不到项目 {name}。请先使用 'init' 命令初始化。")
        return

    logger.info(f"正在获取链接信息：{url} ...")
    videos = YouTubeService.get_video_info(url)
    config = project.load_config()

    new_count = 0
    for v in videos:
        if any(existing["url"] == v["url"] for existing in config["videos"]):
            continue

        v_id = f"v{len(config['videos']) + 1:03d}"
        v["id"] = v_id
        v["status"] = "pending"
        v["dir"] = v_id
        config["videos"].append(v)
        new_count += 1

    project.save_config(config)
    logger.info(f"成功向项目 {name} 中添加了 {new_count} 个新视频。")


@app.command()
def list():
    """
    列出所有项目及其进度
    """
    pm = ProjectManager()
    projects = pm.list_projects()
    if not projects:
        logger.info("当前没有任何项目。")
        return
    print(f"{'项目名称':<20} | {'所属行业':<30} | {'处理进度':<10}")
    print("-" * 65)
    for p in projects:
        print(
            f"{p['name']:<20} | {', '.join(p['industries']):<30} | {p['progress']:<10}"
        )


@app.command()
def run(
    name: str = typer.Argument(..., help="项目名称"),
):
    """
    开始执行项目任务（下载、转录、翻译、压制）
    """
    debug = state["debug"]
    pm = ProjectManager()
    project = pm.get_project(name)
    if not project.exists():
        logger.error(f"找不到项目 {name}。")
        return

    config = project.load_config()
    glossary = project.load_glossary()
    ai = AIService(debug=debug)

    pending_videos = [v for v in config["videos"] if v["status"] != "completed"]
    if not pending_videos:
        logger.info("没有待处理的视频。")
        return

    project_pbar = tqdm(
        pending_videos,
        desc=f"项目进度: {name}",
        unit="视频",
        disable=debug,
    )

    for v in project_pbar:
        v_title_short = (v["title"][:30] + "..") if len(v["title"]) > 32 else v["title"]
        if not debug:
            project_pbar.set_postfix({"当前视频": v_title_short})

        logger.info(f"开始处理视频: {v['title']}")

        v_dir = project.videos_dir / v["dir"]
        v_dir.mkdir(parents=True, exist_ok=True)

        video_path = v_dir / "raw.mp4"
        audio_path = v_dir / "audio.mp3"
        original_srt_path = v_dir / "original.srt"
        translated_srt_path = v_dir / "translated.srt"
        output_path = v_dir / "output.mp4"

        try:
            if not video_path.exists():
                logger.info(f"正在从 YouTube 下载视频...")
                YouTubeService.download_highest_quality(v["url"], video_path)

            if config["settings"]["get_subtitle"] and not original_srt_path.exists():
                logger.info("正在提取视频音频...")
                VideoService.extract_audio(video_path, audio_path)
                logger.info("正在使用本地 Whisper 模型进行转录...")
                srt_content = ai.transcribe(audio_path)
                with open(original_srt_path, "w", encoding="utf-8") as f:
                    f.write(srt_content)

            if (
                config["settings"]["translate_subtitle"]
                and not translated_srt_path.exists()
            ):
                logger.info("正在调用 DeepSeek 进行字幕翻译...")
                with open(original_srt_path, "r", encoding="utf-8") as f:
                    original_srt_content = f.read()
                translated_srt = ai.translate_srt(original_srt_content, glossary)
                with open(translated_srt_path, "w", encoding="utf-8") as f:
                    f.write(translated_srt)

            burn_mode = config["settings"].get("burn_mode", "double")
            if burn_mode == "none":
                logger.info("当前模式为 none，跳过字幕压制步骤。")
            else:
                logger.info(f"正在压制字幕 (模式: {burn_mode})...")
                VideoService.burn_subtitles(
                    video_path,
                    output_path,
                    original_srt_path if original_srt_path.exists() else None,
                    translated_srt_path if translated_srt_path.exists() else None,
                    mode=burn_mode,
                )

            v["status"] = "completed"
            project.save_config(config)
            logger.info(f"处理成功: {v['title']}")

        except Exception as e:
            msg = f"处理视频 {v['title']} 时出错: {e}"
            if debug:
                logger.exception(msg)
            else:
                logger.error(msg)
            v["status"] = "failed"
            project.save_config(config)


@app.command()
def glossary(
    name: str = typer.Argument(..., help="项目名称"),
    industry: str = typer.Option("", "--industry", "-i", help="新的行业领域"),
):
    """
    更新项目的行业术语表
    """
    pm = ProjectManager()
    project = pm.get_project(name)
    if not project.exists():
        logger.error(f"找不到项目 {name}。")
        return

    config = project.load_config()
    industries = industry.split(",") if industry else config.get("industries", [])
    industries = [i.strip() for i in industries]

    logger.info(f"正在为项目 {name} 更新术语表，行业领域：{industries}...")
    ai = AIService()
    new_glossary = ai.generate_glossary(industries)

    current_glossary = project.load_glossary()
    current_glossary.update(new_glossary)
    project.save_glossary(current_glossary)

    if industry:
        config["industries"] = industries
        project.save_config(config)

    logger.info(f"术语表更新完成。当前共包含 {len(current_glossary)} 个术语。")
