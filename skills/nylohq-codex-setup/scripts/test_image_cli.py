"""Offline image fallback tests; never use member credentials or the network."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import image_cli as image


class ImageCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="nylohq-image-test-")
        self.home = Path(self.temp.name) / "Member O'Brien ü" / ".codex"
        (self.home / "nylohq-lb").mkdir(parents=True)
        (self.home / "nylohq-lb/api-key").write_text("fixture-member-key")
        (self.home / "config.toml").write_text(
            'model_provider="nylohq_voice_audit"\n'
            '[model_providers.nylohq_voice_audit]\n'
            'base_url="https://codex.nylohq.com/v1"\n'
        )
        self.cli = self.home / "image cli.py"
        self.cli.write_text("# Fixture only\n")

    def tearDown(self):
        self.temp.cleanup()

    def test_only_child_receives_existing_key_and_endpoint(self):
        before = (self.home / "config.toml").read_bytes()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "unrelated", "OPENAI_BASE_URL": "https://wrong.invalid", "OPENAI_PROJECT_ID": "other"}), patch.object(image.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "Wrote image.png\n", "")) as run, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(image.run_image_cli(self.home, self.cli, ["generate", "--prompt", "hello"]), 0)
            command = run.call_args.args[0]
            env = run.call_args.kwargs["env"]
            self.assertNotIn("fixture-member-key", " ".join(command))
            self.assertEqual(env["OPENAI_API_KEY"], "fixture-member-key")
            self.assertEqual(env["OPENAI_BASE_URL"], image.s.API)
            self.assertNotIn("OPENAI_PROJECT_ID", env)
            self.assertEqual(os.environ["OPENAI_API_KEY"], "unrelated")
        self.assertEqual((self.home / "config.toml").read_bytes(), before)

    def test_wrong_destination_is_rejected_before_starting_child(self):
        p = self.home / "config.toml"
        p.write_text(p.read_text().replace(image.s.API, "https://elsewhere.invalid/v1"))
        with patch.object(image.subprocess, "run") as run, self.assertRaises(image.s.SetupError):
            image.run_image_cli(self.home, self.cli, ["generate"])
        run.assert_not_called()

    def test_profile_is_not_silently_ignored(self):
        p = self.home / "config.toml"
        p.write_text('profile="team"\n' + p.read_text())
        with self.assertRaises(image.s.SetupError):
            image.image_context(self.home)

    def test_child_failure_and_key_redaction(self):
        output, error = io.StringIO(), io.StringIO()
        result = subprocess.CompletedProcess([], 7, "fixture-member-key", "error fixture-member-key")
        with patch.object(image.subprocess, "run", return_value=result), contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            self.assertEqual(image.run_image_cli(self.home, self.cli, ["generate"]), 7)
        self.assertNotIn("fixture-member-key", output.getvalue() + error.getvalue())
        self.assertIn("[REDACTED]", output.getvalue())

    def test_check_sends_no_request_and_prints_no_secret(self):
        output = io.StringIO()
        with patch.object(image.subprocess, "run") as run, contextlib.redirect_stdout(output):
            code = image.main(["--home", str(self.home), "--image-cli", str(self.cli), "--check"])
        self.assertEqual(code, 0)
        self.assertFalse(json.loads(output.getvalue())["request_sent"])
        self.assertNotIn("fixture-member-key", output.getvalue())
        run.assert_not_called()

    def test_missing_key_and_cli_stop(self):
        (self.home / "nylohq-lb/api-key").unlink()
        with self.assertRaises(image.s.SetupError):
            image.image_context(self.home)
        (self.home / "nylohq-lb/api-key").write_text("fixture-member-key")
        with self.assertRaises(image.s.SetupError):
            image.run_image_cli(self.home, self.home / "absent.py", ["generate"])

    def test_wrapper_executes_bundled_cli_without_shell_quoting(self):
        self.cli.write_text(
            "import os,sys\n"
            "assert os.environ['OPENAI_BASE_URL']=='https://codex.nylohq.com/v1'\n"
            "assert os.environ['OPENAI_API_KEY']=='fixture-member-key'\n"
            "assert sys.argv[1:]==['generate','--prompt',\"O'Brien $name; ü\"]\n"
            "print('fixture completed')\n"
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(image.run_image_cli(self.home, self.cli, ["generate", "--prompt", "O'Brien $name; ü"]), 0)
        self.assertIn("fixture completed", output.getvalue())


if __name__ == "__main__":
    unittest.main()
