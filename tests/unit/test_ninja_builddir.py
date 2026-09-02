# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""The generated build.ninja must declare `builddir`.

Ninja keeps `.ninja_log` and `.ninja_deps` in the directory named by the
top-level `builddir` variable, and falls back to the cwd when it is absent.
`ebuild build` runs ninja with `-f <build_dir>/build.ninja` from the project
root, so without `builddir` that state was written into the source tree:
it showed up as untracked files, `ebuild clean` removed `_build/` but left
it behind, and every `--build-dir` of one project shared a single log.
"""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ebuild.build.ninja_backend import NinjaBackend
from ebuild.core.config import ProjectConfig, TargetConfig


def _toolchain():
    return SimpleNamespace(cc="cc", cxx="c++", ar="ar")


class TestNinjaBuilddir(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)

    def _generate(self, name: str) -> tuple[Path, str]:
        build_dir = Path(self._tmpdir.name) / name
        target = TargetConfig(
            name="app", target_type="executable", sources=["src/main.c"]
        )
        config = ProjectConfig(
            name="proj", version="1.0", targets=[target], source_dir=build_dir
        )
        NinjaBackend(config, build_dir, _toolchain()).generate()
        return build_dir, (build_dir / "build.ninja").read_text(encoding="utf-8")

    def test_builddir_is_declared(self):
        """Without this line ninja falls back to the cwd for its state files."""
        build_dir, text = self._generate("_build")
        self.assertIn(f"builddir = {build_dir}", text)

    def test_builddir_points_at_the_requested_build_dir(self):
        """Two build dirs must not share one .ninja_log."""
        debug_dir, debug_text = self._generate("build-debug")
        release_dir, release_text = self._generate("build-release")

        self.assertIn(f"builddir = {debug_dir}", debug_text)
        self.assertIn(f"builddir = {release_dir}", release_text)
        self.assertNotIn(str(release_dir), debug_text)

    def test_builddir_precedes_first_rule(self):
        """Ninja only honours builddir as a top-level variable, so it has to
        appear before the rules rather than anywhere in the file."""
        _, text = self._generate("_build")
        self.assertLess(text.index("builddir ="), text.index("rule cc"))


if __name__ == "__main__":
    unittest.main()
