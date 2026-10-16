"""Opt-in negative CI demonstration: a corrupted temporary fixture must fail visibly."""

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.check_wp1_fixtures import DEFAULT_DIRECTORY, verify_suite


def main():
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary) / "fixtures"
        shutil.copytree(DEFAULT_DIRECTORY, directory)
        with (directory / "heat.csv").open("ab") as stream:
            stream.write(b"deliberately corrupted synthetic fixture\n")
        try:
            verify_suite(directory)
        except ValueError:
            print("Controlled CI failure: corrupted synthetic input was rejected.", file=sys.stderr)
            return 1
        print("Failure probe invalid: corrupted input was accepted.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
