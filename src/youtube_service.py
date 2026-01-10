import yt_dlp
import os
from pathlib import Path


class YouTubeService:
    @staticmethod
    def get_video_info(url: str):
        ydl_opts = {
            "quiet": True,
            "extract_flat": True,
            "force_generic_extractor": False,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if "entries" in info:
                return [
                    {"url": entry["url"], "title": entry.get("title", "Unknown")}
                    for entry in info["entries"]
                ]
            else:
                return [
                    {"url": info["webpage_url"], "title": info.get("title", "Unknown")}
                ]

    @staticmethod
    def download_highest_quality(url: str, output_path: Path):
        """
        Download highest quality video and audio, merge into mp4.
        """
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": str(output_path),
            "merge_output_format": "mp4",
            "quiet": False,
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return output_path
