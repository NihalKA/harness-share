"""Offline installation tests using temporary homes; no credentials or network."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import image_defaults as defaults


class ImageDefaultsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="nylohq-default-test-")
        self.home = Path(self.temp.name) / "Member O'Brien ü" / ".codex"
        self.skills = self.home / "skills"
        helper = self.skills / "nylohq-codex-setup/scripts/image_cli.py"
        helper.parent.mkdir(parents=True)
        helper.write_text("# fixture helper\n")

    def tearDown(self):
        self.temp.cleanup()

    def test_install_preserves_user_instructions_and_backs_up(self):
        original = b"# Existing preferences\nUse concise replies.\n"
        (self.home / "AGENTS.md").write_bytes(original)
        result = defaults.install(self.home, self.skills)
        self.assertEqual(result["status"], "configured")
        self.assertTrue((self.home / "AGENTS.md").read_bytes().startswith(original))
        self.assertEqual((Path(result["backup"]) / "0.before").read_bytes(), original)
        self.assertTrue((self.skills / "nylohq-imagegen/SKILL.md").is_file())
        self.assertIn(str(self.skills / "nylohq-codex-setup/scripts/image_cli.py"), (self.home / "AGENTS.md").read_text())

    def test_repeat_does_not_duplicate_preference_or_backup(self):
        defaults.install(self.home, self.skills)
        before = (self.home / "AGENTS.md").read_bytes()
        count = len(list((self.home / "backups").iterdir()))
        result = defaults.install(self.home, self.skills)
        self.assertEqual(result["status"], "already_configured")
        self.assertEqual((self.home / "AGENTS.md").read_bytes(), before)
        self.assertEqual(len(list((self.home / "backups").iterdir())), count)

    def test_no_choice_writes_nothing(self):
        with contextlib.redirect_stdout(io.StringIO()):
            code = defaults.main(["--home", str(self.home), "--skills-dir", str(self.skills)])
        self.assertEqual(code, 1)
        self.assertFalse((self.home / "AGENTS.md").exists())

    def test_malformed_markers_preserve_file(self):
        value = (defaults.START + "\nExisting content\n").encode()
        (self.home / "AGENTS.md").write_bytes(value)
        with self.assertRaises(defaults.s.SetupError):
            defaults.install(self.home, self.skills)
        self.assertEqual((self.home / "AGENTS.md").read_bytes(), value)

    def test_failure_rolls_back_written_targets(self):
        original = b"Existing instructions\n"
        (self.home / "AGENTS.md").write_bytes(original)
        real_write = defaults.s.atomic_write

        def fail_one(path, value):
            if path == self.skills / "nylohq-imagegen/SKILL.md":
                raise OSError("fixture failure")
            return real_write(path, value)

        with patch.object(defaults.s, "atomic_write", side_effect=fail_one), self.assertRaises(OSError):
            defaults.install(self.home, self.skills)
        self.assertEqual((self.home / "AGENTS.md").read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
