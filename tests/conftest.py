from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory
from typing import Generator

import pytest


@pytest.fixture
def fixture_path() -> Generator[Path, None, None]:
    yield Path(__file__).parent / "fixtures"


@pytest.fixture
def e2e_path(fixture_path: Path) -> Generator[Path, None, None]:
    yield fixture_path / "e2e"


@pytest.fixture
def e2e_revision_assets(e2e_path: Path) -> Generator[Path, None, None]:
    with TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        asset_path = temp_dir_path / "assets"
        copytree(e2e_path / "revision", asset_path)
        yield asset_path


@pytest.fixture
def e2e_revision_reference_alembic_assets(e2e_revision_assets: Path) -> Generator[Path, None, None]:
    yield e2e_revision_assets / "reference"


@pytest.fixture
def e2e_revision_sut_alembic_assets(e2e_revision_assets: Path) -> Generator[Path, None, None]:
    yield e2e_revision_assets / "sut"
