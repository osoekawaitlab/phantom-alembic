import importlib
import os
import sys
from argparse import ArgumentParser

from .core import PhantomAlembic


def load_object_from_path(path_str: str) -> PhantomAlembic:
    """
    'path/to/file.py:object' または 'module:object' 形式の文字列からオブジェクトをロードする
    """
    if ":" not in path_str:
        raise ValueError("Path must be in format 'path/to/file.py:object' or 'module:object'")

    path, attr_name = path_str.split(":", 1)

    if os.path.exists(path) or path.endswith(".py"):
        if path.endswith(".py"):
            module_name = os.path.basename(path)[:-3]  # .pyを除去
        else:
            module_name = os.path.basename(path)

        abs_path = os.path.abspath(path)

        if not abs_path.endswith(".py") and os.path.isfile(abs_path + ".py"):
            abs_path += ".py"

        spec = importlib.util.spec_from_file_location(module_name, abs_path)
        if spec is None:
            raise ImportError(f"Could not load spec for {abs_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        ldr = spec.loader
        if ldr is None:
            raise ImportError(f"Could not load spec for {abs_path}")
        ldr.exec_module(module)
    else:
        try:
            module = importlib.import_module(path)
        except ImportError:
            original_path = sys.path.copy()
            sys.path.insert(0, os.getcwd())
            try:
                module = importlib.import_module(path)
            finally:
                sys.path = original_path

    obj = module
    for part in attr_name.split("."):
        obj = getattr(obj, part)

    if not isinstance(obj, PhantomAlembic):
        raise ValueError(f"Object {obj} is not a PhantomAlembic")

    return obj


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("module", type=str)
    subcommands = parser.add_subparsers(dest="command")
    revision_parser = subcommands.add_parser("revision")
    revision_parser.add_argument("--message", "-m", default=None, type=str, nargs="?")
    revision_parser.add_argument("--autogenerate", "-a", action="store_true")
    args = parser.parse_args()
    phantom_alembic = load_object_from_path(args.module)
    if args.command == "revision":
        phantom_alembic.revision(message=args.message, autogenerate=args.autogenerate)
