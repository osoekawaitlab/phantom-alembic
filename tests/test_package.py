import re

import phantom_alembic


def test_phantom_alembic_has_version() -> None:
    assert re.match(r"^\d+\.\d+\.\d+$", phantom_alembic.__version__)
