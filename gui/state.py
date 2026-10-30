"""Small persistent application preferences for FloodGuard Studio."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from floodguard.paths import projects_directory, reports_directory


def config_directory() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "FloodGuardStudio"


def settings_path() -> Path:
    return config_directory() / "settings.json"


@dataclass
class AppSettings:
    default_project_directory: str = field(
        default_factory=lambda: str(projects_directory())
    )
    default_reports_directory: str = field(
        default_factory=lambda: str(reports_directory())
    )
    default_area_ha: float = 5.0
    default_rainfall_intensity_mm_h: float = 90.0
    default_runoff_coefficient: float = 0.75
    confirm_delete: bool = True
    show_scope_notes: bool = True
    recent_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> AppSettings:
        defaults = cls()
        if not isinstance(data, dict):
            return defaults

        def number(key: str, fallback: float) -> float:
            value = data.get(key, fallback)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return fallback
            return float(value)

        def text(key: str, fallback: str) -> str:
            value = data.get(key, fallback)
            return value if isinstance(value, str) and value.strip() else fallback

        def boolean(key: str, fallback: bool) -> bool:
            value = data.get(key, fallback)
            return value if isinstance(value, bool) else fallback

        recent = data.get("recent_files", [])
        recent_files = (
            [item for item in recent if isinstance(item, str)]
            if isinstance(recent, list)
            else []
        )
        return cls(
            default_project_directory=text(
                "default_project_directory", defaults.default_project_directory
            ),
            default_reports_directory=text(
                "default_reports_directory", defaults.default_reports_directory
            ),
            default_area_ha=number("default_area_ha", defaults.default_area_ha),
            default_rainfall_intensity_mm_h=number(
                "default_rainfall_intensity_mm_h",
                defaults.default_rainfall_intensity_mm_h,
            ),
            default_runoff_coefficient=number(
                "default_runoff_coefficient", defaults.default_runoff_coefficient
            ),
            confirm_delete=boolean("confirm_delete", defaults.confirm_delete),
            show_scope_notes=boolean("show_scope_notes", defaults.show_scope_notes),
            recent_files=recent_files[:10],
        )

    def remember_recent(self, path: str | Path) -> None:
        resolved = str(Path(path).resolve())
        self.recent_files = [
            item for item in self.recent_files if Path(item) != Path(resolved)
        ]
        self.recent_files.insert(0, resolved)
        self.recent_files = self.recent_files[:8]

    @classmethod
    def load(cls, path: Path | None = None) -> AppSettings:
        source = path or settings_path()
        try:
            return cls.from_dict(json.loads(source.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return cls()

    def save(self, path: Path | None = None) -> Path:
        destination = path or settings_path()
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8"
        )
        os.replace(temporary, destination)
        return destination
