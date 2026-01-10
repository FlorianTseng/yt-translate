import os
import logging
from openai import OpenAI
from pathlib import Path
import json
from faster_whisper import WhisperModel


class AIService:
    def __init__(self, debug: bool = False):
        self.logger = logging.getLogger("AIService")
        self.debug = debug
        # DeepSeek Config
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com"),
        )
        self.chat_model = os.getenv("CHAT_MODEL", "deepseek-chat")

        # Local Whisper Config
        self.whisper_model_size = os.getenv("WHISPER_MODEL", "base")
        self.whisper_model = None  # Lazy load

    def _get_whisper(self):
        if self.whisper_model is None:
            self.logger.info(
                f"Loading local Whisper model ({self.whisper_model_size})..."
            )
            self.whisper_model = WhisperModel(
                self.whisper_model_size, device="cpu", compute_type="int8"
            )
        return self.whisper_model

    def generate_glossary(self, industries: list) -> dict:
        combined_glossary = {}
        if not industries:
            return {}

        per_industry = 60

        for industry in industries:
            self.logger.info(
                f"Generating glossary for industry: {industry} (target: {per_industry} terms)"
            )
            prompt = f"""你是一位精通{industry}领域的翻译专家。
            请提供一份该领域最核心、最常用的 {per_industry} 个技术术语及其对应的简体中文 (zh-cn) 标准译名。
            仅输出一个 JSON 对象，键为英文术语，值为中文翻译。"""

            try:
                response = self.client.chat.completions.create(
                    model=self.chat_model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content
                if content:
                    industry_glossary = json.loads(content)
                    combined_glossary.update(industry_glossary)
            except Exception as e:
                self.logger.error(f"Failed to generate glossary for {industry}: {e}")

        return combined_glossary

    def transcribe(self, audio_path: Path) -> str:
        self.logger.info(f"Transcribing audio: {audio_path}")
        model = self._get_whisper()

        # Optimization for environment noise and subtitle length:
        # word_timestamps=True allows more granular control over segments
        segments, info = model.transcribe(
            str(audio_path),
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            initial_prompt="This is a technical video about computer science and industry trends.",
            # Control subtitle length (characters)
            word_timestamps=True,
        )

        self.logger.info(
            f"Detected language: {info.language} ({info.language_probability:.2f})"
        )

        srt_lines = []
        index = 1

        # Max characters per line and max duration to split long segments
        max_chars = 150

        for segment in segments:
            text = segment.text.strip()

            # If segment is too long, we can try to split it based on words or simple character count
            if len(text) > max_chars:
                # Simple split logic: try to split by words to keep it under max_chars
                words = text.split()
                current_chunk = []
                current_len = 0

                # Estimate timing for sub-segments based on character ratio if word timestamps aren't perfectly mapped
                # For simplicity and robustness, we split the segment into chunks
                duration = segment.end - segment.start
                total_chars = len(text)

                start_time = segment.start
                for word in words:
                    if current_len + len(word) + 1 > max_chars and current_chunk:
                        # Flush current chunk
                        chunk_text = " ".join(current_chunk)
                        chunk_chars = len(chunk_text)
                        chunk_duration = (chunk_chars / total_chars) * duration
                        end_time = start_time + chunk_duration

                        srt_lines.append(
                            f"{index}\n{self._format_timestamp(start_time)} --> {self._format_timestamp(end_time)}\n{chunk_text}\n"
                        )
                        index += 1

                        start_time = end_time
                        current_chunk = [word]
                        current_len = len(word)
                    else:
                        current_chunk.append(word)
                        current_len += len(word) + 1

                if current_chunk:
                    chunk_text = " ".join(current_chunk)
                    srt_lines.append(
                        f"{index}\n{self._format_timestamp(start_time)} --> {self._format_timestamp(segment.end)}\n{chunk_text}\n"
                    )
                    index += 1
            else:
                if self.debug:
                    self.logger.debug(
                        f"Segment {index}: [{segment.start:.2f}s -> {segment.end:.2f}s] {text}"
                    )
                start = self._format_timestamp(segment.start)
                end = self._format_timestamp(segment.end)
                srt_lines.append(f"{index}\n{start} --> {end}\n{text}\n")
                index += 1

        return "\n".join(srt_lines)

    def _format_timestamp(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def translate_srt(self, srt_content: str, glossary: dict) -> str:
        # Split SRT into batches to avoid truncation
        batches = self._split_srt(srt_content, batch_size=60)  # ~60 subtitles per batch
        translated_batches = []

        glossary_str = json.dumps(glossary, ensure_ascii=False)

        for idx, batch in enumerate(batches):
            self.logger.info(f"Translating batch {idx + 1}/{len(batches)}...")
            prompt = f"""你是一位专业的翻译官。请将以下 SRT 字幕内容翻译成简体中文 (zh-cn)。
            规则：
            1. 严格保留 SRT 格式（时间戳和序号）。
            2. 必须参考以下技术术语表以保证一致性：{glossary_str}。
            3. 翻译要自然、地道，符合技术语境。
            4. 仅输出翻译后的 SRT 内容，不要包含任何解释。
            
            SRT 内容：
            {batch}"""

            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个翻译助手，专门处理 SRT 文件。",
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            content = response.choices[0].message.content
            if content:
                translated_batches.append(content.strip())

        return "\n\n".join(translated_batches)

    def _split_srt(self, srt_content: str, batch_size: int) -> list:
        """Splits SRT content into batches of subtitles."""
        lines = srt_content.strip().split("\n")
        subtitles = []
        current_sub = []

        for line in lines:
            if line.strip().isdigit() and current_sub and current_sub[-1] == "":
                # New subtitle starts
                subtitles.append("\n".join(current_sub))
                current_sub = [line]
            else:
                current_sub.append(line)

        if current_sub:
            subtitles.append("\n".join(current_sub))

        # Group into batches
        batches = []
        for i in range(0, len(subtitles), batch_size):
            batches.append("\n\n".join(subtitles[i : i + batch_size]))

        return batches
