import os
import argparse
import logging
from dotenv import load_dotenv
from pathlib import Path
from src.project_manager import ProjectManager
from src.youtube_service import YouTubeService
from src.ai_service import AIService
from src.video_service import VideoService
from tqdm import tqdm

load_dotenv()


def setup_logging(debug: bool):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Set faster-whisper and other noisy libraries to a higher level unless debugging
    if not debug:
        logging.getLogger("faster_whisper").setLevel(logging.WARNING)
        logging.getLogger("openai").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)


def main():
    parser = argparse.ArgumentParser(description="YouTube 视频下载与翻译工具命令行界面")
    parser.add_argument("--debug", action="store_true", help="启用调试日志输出")
    subparsers = parser.add_subparsers(dest="command")

    # init
    init_parser = subparsers.add_parser("init", help="初始化一个新项目")
    init_parser.add_argument("name", help="项目名称")
    init_parser.add_argument(
        "--industry", help="以逗号分隔的行业领域（用于生成术语表）", default=""
    )

    # add
    add_parser = subparsers.add_parser("add", help="向项目中添加视频链接")
    add_parser.add_argument("name", help="项目名称")
    add_parser.add_argument("url", help="YouTube 视频或播放列表链接")

    # list
    subparsers.add_parser("list", help="列出所有项目及其进度")

    # run
    run_parser = subparsers.add_parser(
        "run", help="开始执行项目任务（下载、转录、翻译、压制）"
    )
    run_parser.add_argument("name", help="项目名称")

    # update-glossary
    glossary_parser = subparsers.add_parser(
        "update-glossary", help="更新项目的行业术语表"
    )
    glossary_parser.add_argument("name", help="项目名称")
    glossary_parser.add_argument("--industry", help="新的行业领域")

    args = parser.parse_args()

    setup_logging(args.debug)
    logger = logging.getLogger("CLI")

    if args.command is None:
        parser.print_help()
        return

    pm = ProjectManager()

    if args.command == "init":
        industries = (
            [i.strip() for i in args.industry.split(",")] if args.industry else []
        )
        project = pm.get_project(args.name)
        if project.exists():
            logger.info(f"项目 {args.name} 已存在。")
            return

        logger.info(f"正在初始化项目 {args.name}，所属行业：{industries}...")
        project.init_project(industries)

        ai = AIService()
        glossary = ai.generate_glossary(industries)
        project.save_glossary(glossary)
        logger.info(f"项目初始化完成。AI 自动生成了 {len(glossary)} 个术语。")

    elif args.command == "add":
        project = pm.get_project(args.name)
        if not project.exists():
            logger.error(f"找不到项目 {args.name}。请先使用 'init' 命令初始化。")
            return

        logger.info(f"正在获取链接信息：{args.url} ...")
        videos = YouTubeService.get_video_info(args.url)
        config = project.load_config()

        new_count = 0
        for v in videos:
            # Check if already added
            if any(existing["url"] == v["url"] for existing in config["videos"]):
                continue

            v_id = f"v{len(config['videos']) + 1:03d}"
            v["id"] = v_id
            v["status"] = "pending"
            v["dir"] = v_id
            config["videos"].append(v)
            new_count += 1

        project.save_config(config)
        logger.info(f"成功向项目 {args.name} 中添加了 {new_count} 个新视频。")

    elif args.command == "list":
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

    elif args.command == "run":
        project = pm.get_project(args.name)
        if not project.exists():
            logger.error(f"找不到项目 {args.name}。")
            return

        config = project.load_config()
        glossary = project.load_glossary()
        ai = AIService(debug=args.debug)

        pending_videos = [v for v in config["videos"] if v["status"] != "completed"]
        if not pending_videos:
            logger.info("没有待处理的视频。")
            return

        # Overall progress bar
        project_pbar = tqdm(
            pending_videos,
            desc=f"项目进度: {args.name}",
            unit="视频",
            disable=args.debug,
        )

        for v in project_pbar:
            v_title_short = (
                (v["title"][:30] + "..") if len(v["title"]) > 32 else v["title"]
            )
            if not args.debug:
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
                # 1. Download
                if not video_path.exists():
                    logger.info(f"正在从 YouTube 下载视频...")
                    YouTubeService.download_highest_quality(v["url"], video_path)

                # 2. Transcribe
                if (
                    config["settings"]["get_subtitle"]
                    and not original_srt_path.exists()
                ):
                    logger.info("正在提取视频音频...")
                    VideoService.extract_audio(video_path, audio_path)
                    logger.info("正在使用本地 Whisper 模型进行转录...")
                    srt_content = ai.transcribe(audio_path)
                    with open(original_srt_path, "w", encoding="utf-8") as f:
                        f.write(srt_content)

                # 3. Translate
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

                # 4. Burn
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
                if args.debug:
                    logger.exception(msg)
                else:
                    logger.error(msg)
                v["status"] = "failed"
                project.save_config(config)

    elif args.command == "update-glossary":
        project = pm.get_project(args.name)
        if not project.exists():
            logger.error(f"找不到项目 {args.name}。")
            return

        config = project.load_config()
        industries = (
            args.industry.split(",") if args.industry else config.get("industries", [])
        )
        industries = [i.strip() for i in industries]

        logger.info(f"正在为项目 {args.name} 更新术语表，行业领域：{industries}...")
        ai = AIService()
        new_glossary = ai.generate_glossary(industries)

        # Merge or overwrite? Let's merge for safety
        current_glossary = project.load_glossary()
        current_glossary.update(new_glossary)
        project.save_glossary(current_glossary)

        # Update industries in config if provided
        if args.industry:
            config["industries"] = industries
            project.save_config(config)

        logger.info(f"术语表更新完成。当前共包含 {len(current_glossary)} 个术语。")


if __name__ == "__main__":
    main()
