import json
import os
import re
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
    assert len(version_files) == 1
    with open(version_path / version_files[0], "r", encoding="utf-8") as f:
        expected_version_file_contents = normalize_version_file_contents(f.read())
    sut_proc = spawn(f"phantom_alembic sut:sut revision {options}", cwd=e2e_revision_sut_alembic_assets, env=os.environ)
    sut_proc.expect(EOF)
    sut_proc.close()
    assert sut_proc.exitstatus == 0
    with open(e2e_revision_sut_alembic_assets / "versions.jsonl", "r", encoding="utf-8") as f:
        actual_version_file_contents_list = [
            normalize_version_file_contents(json.loads(ln)["content"]) for ln in f.readlines()
        ]
    assert len(actual_version_file_contents_list) == 1
    actual_version_file_contents = actual_version_file_contents_list[0]
    assert expected_version_file_contents == actual_version_file_contents
