"""Materialize read-only ``DataMount``s into a throwaway working directory.

Files are *copied*, not symlinked: Windows dev environments frequently lack the
privilege to create symlinks, and a copy keeps the child from touching the real
object-store path even by accident.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from vera_core.ports.sandbox import DataMount


def materialize(mounts: list[DataMount]) -> str:
    """Create a fresh temp dir, copy each mount into it by basename, return the dir."""
    workdir = tempfile.mkdtemp(prefix="vera-sandbox-")
    for mount in mounts:
        dest = Path(workdir) / Path(mount.container_path).name
        shutil.copyfile(mount.host_path, dest)
    return workdir


def cleanup(workdir: str) -> None:
    """Remove a directory created by :func:`materialize`. Never raises."""
    shutil.rmtree(workdir, ignore_errors=True)


__all__ = ["cleanup", "materialize"]
