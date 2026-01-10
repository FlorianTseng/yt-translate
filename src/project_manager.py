import os
import json
from pathlib import Path
from typing import List, Optional


class Project:
    def __init__(self, name: str, base_dir: Path):
        self.name = name
        self.path = base_dir / name
        self.config_path = self.path / "project_config.json"
        self.glossary_path = self.path / "glossary.json"
        self.videos_dir = self.path / "videos"

    def exists(self) -> bool:
        return self.config_path.exists()

    def init_project(self, industries: List[str]):
        self.path.mkdir(parents=True, exist_ok=True)
        self.videos_dir.mkdir(exist_ok=True)

        config = {
            "name": self.name,
            "industries": industries,
            "settings": {
                "get_subtitle": True,
                "translate_subtitle": True,
                "burn_mode": "double",
                "target_lang": "zh-cn",
                "_help": {
                    "get_subtitle": "是否通过 AI 提取原视频字幕 (true/false)",
                    "translate_subtitle": "是否调用 DeepSeek 翻译字幕 (true/false)",
                    "burn_mode": "字幕压制模式: 'none' (不执行压制), 'original' (仅压制原语字幕), 'translated' (仅压制翻译字幕), 'double' (双语压制)",
                    "target_lang": "目标翻译语言 (默认 zh-cn)",
                },
            },
            "videos": [],
        }
        self.save_config(config)
        if not self.glossary_path.exists():
            with open(self.glossary_path, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)

    def load_config(self):
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_config(self, config):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def load_glossary(self):
        with open(self.glossary_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_glossary(self, glossary):
        with open(self.glossary_path, "w", encoding="utf-8") as f:
            json.dump(glossary, f, ensure_ascii=False, indent=2)


class ProjectManager:
    def __init__(self, data_root: Optional[str] = None):
        if data_root is None:
            data_root = os.getenv("OUTPUT_ROOT", "output")
        self.data_root = Path(data_root).absolute()
        self.data_root.mkdir(exist_ok=True)

    def get_project(self, name: str) -> Project:
        return Project(name, self.data_root)

    def list_projects(self) -> List[dict]:
        projects = []
        for p in self.data_root.iterdir():
            if p.is_dir() and (p / "project_config.json").exists():
                with open(p / "project_config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                    total_videos = len(config.get("videos", []))
                    completed = len(
                        [
                            v
                            for v in config.get("videos", [])
                            if v.get("status") == "completed"
                        ]
                    )
                    projects.append(
                        {
                            "name": config["name"],
                            "industries": config.get("industries", []),
                            "progress": f"{completed}/{total_videos}",
                        }
                    )
        return projects
