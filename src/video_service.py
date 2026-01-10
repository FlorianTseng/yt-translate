import subprocess
from pathlib import Path


class VideoService:
    @staticmethod
    def extract_audio(video_path: Path, audio_path: Path):
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-acodec",
            "libmp3lame",
            "-q:a",
            "4",
            str(audio_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)

    @staticmethod
    def burn_subtitles(
        video_path: Path,
        output_path: Path,
        original_srt: Path | None = None,
        translated_srt: Path | None = None,
        mode: str = "double",
    ):
        """
        Burn subtitles using ffmpeg filters.
        mode: "double", "original", "translated", "none"
        Alignment: 2=bottom-center, 6=top-center
        Colors: &HFFFFFF=White, &H00FFFF=Yellow
        """
        if mode == "none" or (not original_srt and not translated_srt):
            # Just copy or symlink if no subtitles
            import shutil

            shutil.copy(video_path, output_path)
            return

        filters = []
        if mode in ["original", "double"] and original_srt:
            # Bottom English (White)
            # escape path for ffmpeg
            esc_original = str(original_srt).replace(":", "\\:").replace("'", "'\\\\''")
            filters.append(
                f"subtitles='{esc_original}':force_style='Alignment=2,FontSize=12,PrimaryColour=&HFFFFFF'"
            )

        if mode in ["translated", "double"] and translated_srt:
            # Top Chinese (Yellow)
            esc_translated = (
                str(translated_srt).replace(":", "\\:").replace("'", "'\\\\''")
            )
            filters.append(
                f"subtitles='{esc_translated}':force_style='Alignment=6,FontSize=12,PrimaryColour=&H00FFFF'"
            )

        filter_str = ",".join(filters)

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vf",
            filter_str,
            "-c:a",
            "copy",  # Keep original audio
            str(output_path),
        ]
        subprocess.run(cmd, check=True)
