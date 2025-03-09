import json
from contextlib import AbstractContextManager
from pathlib import Path
from tempfile import TemporaryDirectory
from types import TracebackType
from typing import Optional, Type

from alembic import command
from alembic.config import Config

from .defaults import ENV_CONTENT_TEMPLATE, SCRIPT_MAKO_STRING


class PhantomAlembicContext(AbstractContextManager["PhantomAlembicContext"]):
    def __init__(self, phantom_alembic: "PhantomAlembic", dir_path: Path) -> None:
        self._phantom_alembic = phantom_alembic
        self._dir_path = dir_path

    @property
    def phantom_alembic(self) -> "PhantomAlembic":
        return self._phantom_alembic

    @property
    def version_data_path(self) -> Path:
        return self.phantom_alembic.version_data_path

    @property
    def migrations_path(self) -> Path:
        return self.phantom_alembic._get_migrations_path(self.dir_path)

    @property
    def version_path(self) -> Path:
        return self.phantom_alembic._get_version_path(self.dir_path)

    @property
    def dir_path(self) -> Path:
        return self._dir_path

    @property
    def alembic_config(self) -> Config:
        return self.phantom_alembic.gen_alembic_config(self.dir_path)

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        if exc_val is not None:
            raise exc_val
        with open(self.version_data_path, "w", encoding="utf-8") as fout:
            for fn in self.version_path.glob("*.py"):
                with open(fn, "r", encoding="utf-8") as fin:
                    fout.write(json.dumps({"name": fn.name, "content": fin.read()}))
                    fout.write("\n")

    def __enter__(self) -> "PhantomAlembicContext":
        self.version_path.mkdir(parents=True, exist_ok=True)
        if self.phantom_alembic.ini_content is not None:
            with open(self.dir_path / "alembic.ini", "w", encoding="utf-8") as f:
                f.write(self.phantom_alembic.ini_content)
        with open(self.migrations_path / "env.py", "w", encoding="utf-8") as f:
            f.write(self.phantom_alembic.env_content)
        with open(self.migrations_path / "script.py.mako", "w", encoding="utf-8") as f:
            f.write(SCRIPT_MAKO_STRING)
        if self.version_data_path.exists():
            with open(self.version_data_path, "r", encoding="utf-8") as f:
                version_data = [json.loads(ln.strip()) for ln in f.readlines()]
        else:
            version_data = []
        for version_data_item in version_data:
            with open(self.version_path / version_data_item["name"], "w", encoding="utf-8") as f:
                f.write(version_data_item["content"])
        return self


class PhantomAlembic:
    def __init__(
        self,
        version_data_path: Path,
        ini_content: Optional[str] = None,
        env_content: Optional[str] = None,
    ) -> None:
        self._ini_content = ini_content
        self._version_data_path = version_data_path
        self._env_content = env_content

    @property
    def version_data_path(self) -> Path:
        return self._version_data_path

    @property
    def ini_content(self) -> str | None:
        return self._ini_content

    @property
    def env_content(self) -> str:
        if self._env_content is None:
            return ENV_CONTENT_TEMPLATE.format()
        return self._env_content

    def _get_migrations_path(self, temp_dir_path: Path) -> Path:
        return temp_dir_path / "migrations"

    def _get_version_path(self, temp_dir_path: Path) -> Path:
        return self._get_migrations_path(temp_dir_path) / "versions"

    def gen_alembic_config(self, asset_path: Path) -> Config:
        if self.ini_content is not None:
            config = Config(asset_path / "alembic.ini")
        else:
            config = Config()
        config.set_main_option("script_location", str(self._get_migrations_path(asset_path)))
        config.set_main_option("version_path", str(self._get_version_path(asset_path)))
        return config

    def revision(self, message: Optional[str] = None, autogenerate: bool = False) -> None:
        with TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            with PhantomAlembicContext(self, temp_dir_path) as context:
                command.revision(
                    context.alembic_config,
                    message=message if message is not None else "empty message",
                    autogenerate=autogenerate,
                )
