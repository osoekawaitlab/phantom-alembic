import json
import os
import re
import sqlite3
from pathlib import Path

from pexpect import EOF, spawn
from pytest import mark


def normalize_version_file_contents(contents: str) -> str:
    return "\n".join(
        re.sub(
            r"Revision ID: .*$",
            "Revision ID: <revision_id>",
            re.sub(
                r"Create Date: .*$",
                "Create Date: <create_date>",
                re.sub(r"revision: str = .*$", "revision: str = <revision>", ln),
            ),
        )
        for ln in contents.split("\n")
    )


@mark.parametrize("options", ["", '-m "hoge hoge"', '--message "hoge hoge"', '--autogenerate -m "message"'])
def test_e2e_revision(
    e2e_revision_reference_alembic_assets: Path, e2e_revision_sut_alembic_assets: Path, options: str
) -> None:
    reference_proc = spawn(f"alembic revision {options}", cwd=e2e_revision_reference_alembic_assets, env=os.environ)
    reference_proc.expect(EOF)
    reference_proc.close()
    assert reference_proc.exitstatus == 0
    version_path = e2e_revision_reference_alembic_assets / "migrations" / "versions"
    version_files = list(filter(lambda f: f.endswith(".py"), os.listdir(version_path)))
    assert len(version_files) == 2
    reference_version_file_name_to_content_list = []
    for fn in version_files:
        with open(version_path / fn, "r", encoding="utf-8") as f:
            reference_version_file_name_to_content_list.append(normalize_version_file_contents(f.read()))
    reference_version_file_name_to_content_list.sort()
    sut_proc = spawn(f"phantom_alembic sut:sut revision {options}", cwd=e2e_revision_sut_alembic_assets, env=os.environ)
    sut_proc.expect(EOF)
    sut_proc.close()
    if sut_proc.exitstatus != 0:
        print(sut_proc.before)
    assert sut_proc.exitstatus == 0
    with open(e2e_revision_sut_alembic_assets / "versions.jsonl", "r", encoding="utf-8") as f:
        actual_version_file_name_to_content_list = sorted(
            normalize_version_file_contents(o["content"]) for o in (json.loads(ln) for ln in f.readlines())
        )
    assert len(actual_version_file_name_to_content_list) == 2
    assert reference_version_file_name_to_content_list == actual_version_file_name_to_content_list


def test_e2e_upgrade(e2e_upgrade_reference_alembic_assets: Path, e2e_upgrade_sut_alembic_assets: Path) -> None:
    reference_proc = spawn("alembic upgrade head", cwd=e2e_upgrade_reference_alembic_assets, env=os.environ)
    reference_proc.expect(EOF)
    reference_proc.close()
    assert reference_proc.exitstatus == 0
    sut_proc = spawn("phantom_alembic sut:sut upgrade head", cwd=e2e_upgrade_sut_alembic_assets, env=os.environ)
    sut_proc.expect(EOF)
    sut_proc.close()
    if sut_proc.exitstatus != 0:
        print(sut_proc.before)
    assert sut_proc.exitstatus == 0
    with (
        sqlite3.connect(e2e_upgrade_reference_alembic_assets / "test.db") as reference_conn,
        sqlite3.connect(e2e_upgrade_sut_alembic_assets / "test.db") as sut_conn,
    ):
        reference_cursor = reference_conn.cursor()
        reference_cursor.execute("SELECT * FROM sqlite_master WHERE type='table'")
        reference_tables = reference_cursor.fetchall()
        sut_cursor = sut_conn.cursor()
        sut_cursor.execute("SELECT * FROM sqlite_master WHERE type='table'")
        sut_tables = sut_cursor.fetchall()
        assert reference_tables == sut_tables
