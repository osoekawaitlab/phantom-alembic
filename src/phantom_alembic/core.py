import json
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Generator, Optional

from alembic import command
from alembic.config import Config

from .defaults import ENV_CONTENT_STRING, SCRIPT_MAKO_STRING


class PhantomAlembic:
    def __init__(self, ini_content: str, version_data_path: Path) -> None:
        self._ini_content = ini_content
        self._version_data_path = version_data_path

    @property
    def version_data_path(self) -> Path:
        return self._version_data_path

    @property
    def ini_content(self) -> str:
        return self._ini_content

    def _get_migrations_path(self, temp_dir_path: Path) -> Path:
        return temp_dir_path / "migrations"

    def _get_version_path(self, temp_dir_path: Path) -> Path:
        return self._get_migrations_path(temp_dir_path) / "versions"

    @contextmanager
    def _prepare(self) -> Generator[Path, None, None]:
        with TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            with open(temp_dir_path / "alembic.ini", "w", encoding="utf-8") as f:
                f.write(self._ini_content)
            self._get_version_path(temp_dir_path).mkdir(parents=True, exist_ok=True)
            with open(self._get_migrations_path(temp_dir_path) / "env.py", "w", encoding="utf-8") as f:
                f.write(ENV_CONTENT_STRING)
            with open(self._get_migrations_path(temp_dir_path) / "script.py.mako", "w", encoding="utf-8") as f:
                f.write(SCRIPT_MAKO_STRING)
            if self.version_data_path.exists():
                with open(self.version_data_path, "r", encoding="utf-8") as f:
                    version_data = [json.loads(ln) for ln in f.readlines()]
            else:
                version_data = []
            for version_data_item in version_data:
                with open(
                    self._get_version_path(temp_dir_path) / version_data_item["name"], "w", encoding="utf-8"
                ) as f:
                    f.write(version_data_item["content"])
            yield temp_dir_path

    def revision(self, message: Optional[str] = None) -> None:
        with self._prepare() as temp_dir_path:
            config = Config(temp_dir_path / "alembic.ini")
            command.revision(
                config,
                message=message if message is not None else "empty message",
                version_path=str(self._get_version_path(temp_dir_path)),
            )
            with open(self.version_data_path, "w", encoding="utf-8") as fout:
                for fn in self._get_version_path(temp_dir_path).glob("*.py"):
                    with open(fn, "r", encoding="utf-8") as fin:
                        fout.write(json.dumps({"name": fn.name, "content": fin.read()}))
                        fout.write("\n")
