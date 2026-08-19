from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import zipfile


def inspect_wheel(path: Path) -> None:
    name = path.name.lower()
    if name.startswith("tlefinder_core-"):
        allowed_packages = ("tlefinder/core/", "tlefinder/benchmarks/")
        forbidden = ("tlefinder/api/", "tlefinder/gui/", "tlefinder/__init__.py")
        required_dependency = None
    elif name.startswith("tlefinder_api-"):
        allowed_packages = ("tlefinder/api/",)
        forbidden = (
            "tlefinder/core/",
            "tlefinder/benchmarks/",
            "tlefinder/gui/",
            "tlefinder/__init__.py",
        )
        required_dependency = "Requires-Dist: tlefinder-core"
    else:
        raise AssertionError(f"Unexpected wheel name: {path.name}")

    with zipfile.ZipFile(path) as archive:
        members = archive.namelist()
        package_members = [item for item in members if item.startswith("tlefinder/")]
        assert package_members, f"{path.name} contains no tlefinder package files"
        assert all(
            item.startswith(allowed_packages) for item in package_members
        ), f"{path.name} has unowned package files: {package_members}"
        assert not any(
            item == prefix or item.startswith(prefix) for item in members for prefix in forbidden
        ), f"{path.name} contains a forbidden component"

        metadata_paths = [
            item for item in members if PurePosixPath(item).name == "METADATA"
        ]
        assert len(metadata_paths) == 1
        metadata = archive.read(metadata_paths[0]).decode("utf-8")
        if required_dependency:
            assert required_dependency in metadata

    print(f"ownership verified: {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheels", nargs="+", type=Path)
    args = parser.parse_args()
    for wheel in args.wheels:
        inspect_wheel(wheel.resolve())


if __name__ == "__main__":
    main()

