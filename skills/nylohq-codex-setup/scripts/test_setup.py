"""Offline invariants; never read a real user's config or credentials."""
import contextlib
import io
import json
import os
from pathlib import Path, PureWindowsPath
import tempfile
import unittest
from unittest.mock import patch, Mock

import setup as s


def catalog():
    return {"models": [
        {"slug": name, "visibility": visibility, "base_instructions": "Fixture instructions.",
         "supported_reasoning_levels": [{"effort": effort, "description": "Fixture effort"} for effort in ("low", "medium", "high")],
         "display_name": "Fixture model", "description": "Offline test model", "shell_type": "shell_command",
         "supported_in_api": True, "priority": 1, "support_verbosity": True,
         "truncation_policy": {"mode": "tokens", "limit": 10000}, "experimental_supported_tools": [],
         "default_reasoning_level": "medium"}
        for name, visibility in [("gpt-5.6-terra", "list"), ("gpt-6-luna", "list"), ("hidden-model", "hide")]
    ]}


ORIGINAL = b'''# User settings stay intact.
model = "gpt-6-luna" # member preference
model_reasoning_effort = "high"
notify = ["existing-helper", "turn-ended"]
approval_policy = "on-request"

[plugins."browser@example"]
enabled = true

[mcp_servers.local]
command = "existing-tool"
args = ["--a", "b"]

[mcp_servers.local.env]
EXISTING_SETTING = "kept"

[projects.'C:\\Users\\Member\\My Work']
trust_level = "trusted"

[desktop]
followUpQueueMode = "queue"

[[skills.config]]
path = "/existing/skill/SKILL.md"
enabled = false

[model_providers.other]
name = "Other Provider"
base_url = "https://other.invalid/v1"
env_key = "OTHER_KEY"
'''


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="nylohq-offline-test-")
        self.home = Path(self.temp.name) / "Member O'Brien ü" / ".codex"
        self.addCleanup(self.temp.cleanup)
        real_run = s.subprocess.run

        def fixture_run(*args, **kwargs):
            result = real_run(*args, **kwargs)
            # This directory contains no member data. Expose native permission
            # errors in CI while production setup continues to withhold logs.
            if result.returncode:
                self.fail("Fixture permission command failed: " + result.stderr.decode(errors="replace"))
            return result

        with patch.object(s.subprocess, "run", side_effect=fixture_run):
            s.private_dir(self.home / "nylohq-lb")

    def tearDown(self):
        self.temp.cleanup()

    def config(self, original=ORIGINAL):
        return s.build_config(original, self.home, "gpt-6-luna", "high", system="Darwin")[0]

    def fixture_state(self, original=ORIGINAL):
        before = {"config.toml": original, "nylohq-lb/api-key": b"old-fixture-credential", "nylohq-lb/models.json": b'{"old":true}'}
        after = {"config.toml": self.config(original), "nylohq-lb/api-key": b"new-fixture-credential", "nylohq-lb/models.json": json.dumps(catalog()).encode()}
        s.write_state(self.home, before)
        return before, after

    def test_preserves_all_unrelated_values_and_comments(self):
        old = s.parse_config(ORIGINAL).unwrap()
        new = s.parse_config(self.config()).unwrap()
        for key in set(old) - set(s.MANAGED_ROOT) - {"model_providers"}:
            self.assertEqual(old[key], new[key], key)
        self.assertEqual(old["model_providers"]["other"], new["model_providers"]["other"])
        self.assertIn(b"# User settings stay intact.", self.config())
        self.assertIn(b"# member preference", self.config())

    def test_new_config_and_no_duplicate_tables_on_repeat(self):
        once = self.config(None)
        twice = self.config(once)
        self.assertEqual(once, twice)
        parsed = s.parse_config(twice)
        self.assertEqual(parsed["model"], "gpt-6-luna")
        self.assertEqual(parsed["model_providers"]["nylohq_lb"]["wire_api"], "responses")

    def test_root_keys_stay_root_when_input_starts_with_table(self):
        doc = s.parse_config(self.config(b'[desktop]\nfollowUpQueueMode="queue"\n'))
        self.assertIn("model", doc)
        self.assertNotIn("model", doc["desktop"])

    def test_multiline_strings_and_bom(self):
        original = b'\xef\xbb\xbfmodel="gpt-6-luna"\n[custom]\ntext="""one\n[not.a.table]\nmodel = fake\n"""\n'
        doc = s.parse_config(self.config(original))
        self.assertEqual(doc["custom"]["text"], "one\n[not.a.table]\nmodel = fake\n")

    def test_existing_legacy_provider_id_is_preserved(self):
        original = b'model_provider="nylohq_voice_audit"\n[model_providers.nylohq_voice_audit]\nbase_url="https://codex.nylohq.com/v1"\nenv_key="OBSOLETE_KEY"\nrequires_openai_auth=true\n'
        doc = s.parse_config(self.config(original))
        self.assertEqual(doc["model_provider"], "nylohq_voice_audit")
        provider = doc["model_providers"]["nylohq_voice_audit"]
        self.assertNotIn("env_key", provider)
        self.assertNotIn("requires_openai_auth", provider)
        self.assertIn("auth", provider)

    def test_provider_collision_stops(self):
        with self.assertRaises(s.SetupError):
            self.config(b'[model_providers.nylohq_lb]\nbase_url="https://elsewhere.invalid"\n')

    def test_active_default_profile_stops(self):
        with self.assertRaises(s.SetupError):
            self.config(b'profile="team"\n')

    def test_model_preserved_and_prefix_normalized(self):
        doc = {"model": "nylohq/gpt-6-luna", "model_reasoning_effort": "high"}
        self.assertEqual(s.choose_model(doc, catalog()), ("gpt-6-luna", "high"))

    def test_default_terra_and_supported_reasoning(self):
        self.assertEqual(s.choose_model({"model": "not-allowed", "model_reasoning_effort": "ultra"}, catalog()), ("gpt-5.6-terra", "medium"))

    def test_explicit_unavailable_and_hidden_models_fail(self):
        for model in ("not-allowed", "hidden-model"):
            with self.assertRaises(s.SetupError):
                s.choose_model({}, catalog(), model)

    def test_windows_paths_roundtrip_and_literal_quoting(self):
        home = PureWindowsPath(r"C:\Users\O'Brien $name; ü\My Codex")
        ps = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
        data, _ = s.build_config(None, home, "gpt-6-luna", "medium", "Windows", ps)
        doc = s.parse_config(data)
        auth = doc["model_providers"]["nylohq_lb"]["auth"]
        self.assertEqual(auth["command"], ps)
        self.assertEqual(doc["model_catalog_json"], str(home / "nylohq-lb/models.json"))
        command = auth["args"][-1]
        self.assertIn("O''Brien $name; ü", command)
        self.assertIn("ReadAllText('C:", command)
        self.assertNotIn("/bin/cat", data.decode())
        self.assertNotIn("-ExecutionPolicy", auth["args"])

    def test_native_credential_check_keeps_output_private(self):
        path = self.home / "nylohq-lb/api-key"
        s.atomic_write(path, b"fixture-key")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            system = "Windows" if os.name == "nt" else "Darwin"
            s.check_credential(s.credential_config(path, system), "fixture-key")
        self.assertEqual(output.getvalue(), "")

    def test_linux_is_supported_and_other_platforms_still_checked(self):
        for system in ("Linux", "Darwin", "Windows"):
            with patch.object(s.platform, "system", return_value=system):
                self.assertEqual(s.native_os(), system)
        with patch.object(s.platform, "system", return_value="Unsupported"), self.assertRaises(s.SetupError):
            s.native_os()

    def test_linux_text_only_uses_sse_and_preserves_other_settings(self):
        data, provider_id = s.build_config(ORIGINAL, self.home, "gpt-6-luna", "high", system="Linux", text_only=True)
        doc = s.parse_config(data)
        provider = doc["model_providers"][provider_id]
        self.assertFalse(provider["supports_websockets"])
        self.assertEqual(provider["auth"]["command"], "/bin/cat")
        self.assertEqual(provider["auth"]["args"], [str(self.home / "nylohq-lb/api-key")])
        for name in s.MANAGED_ROOT[4:]:
            self.assertNotIn(name, doc)
        old = s.parse_config(ORIGINAL)
        for name in ("plugins", "mcp_servers", "desktop", "projects", "approval_policy"):
            self.assertEqual(doc[name], old[name])

    def test_transport_selection_refresh_and_voice_preservation(self):
        for system in ("Linux", "Darwin", "Windows"):
            for transport in ("sse", "websocket"):
                with self.subTest(system=system, transport=transport):
                    opts = dict(system=system, ps_path="fixture-powershell")
                    once, _ = s.build_config(None, self.home, "gpt-6-luna", "high", transport=transport, **opts)
                    twice, _ = s.build_config(once, self.home, "gpt-6-luna", "high", text_only=True, **opts)
                    self.assertEqual(once, twice)
                    doc = s.parse_config(twice)
                    self.assertEqual(doc["model_providers"][s.DEFAULT_PROVIDER]["supports_websockets"], transport == "websocket")
                    self.assertEqual(doc["experimental_realtime_ws_base_url"], s.API)

    def test_smoke_error_is_actionable_private_and_does_not_retry(self):
        candidate, _ = s.build_config(None, self.home, "gpt-6-luna", "high", system="Linux", text_only=True)
        raw = b'fixture-secret HTTP 429; 503 The previous response operation may still be running; Upstream websocket closed before response.completed'
        proc = Mock(returncode=1, stdout=b'', stderr=raw)
        real_run = s.subprocess.run
        probe_calls = []

        def run_probe(command, **kwargs):
            if command[0] == "fixture-cli":
                probe_calls.append(command)
                return proc
            return real_run(command, **kwargs)

        with patch.object(s, "check_credential"), patch.object(s, "native_os", return_value="Linux"), patch.object(s.subprocess, "run", side_effect=run_probe):
            with self.assertRaises(s.SetupError) as error:
                s.smoke_check("fixture-cli", candidate, json.dumps(catalog()).encode(), self.home / "fixture-key", "fixture-secret", self.home)
        self.assertEqual(len(probe_calls), 1)
        message = str(error.exception)
        self.assertIn("429", message)
        self.assertIn("cooldown", message)
        self.assertIn("LB-to-upstream", message)
        self.assertNotIn("fixture-secret", message)
        probe = s.parse_config((self.home / "config.toml").read_bytes())["model_providers"][s.DEFAULT_PROVIDER]
        for key in ("request_max_retries", "stream_max_retries"):
            self.assertEqual(probe[key], 0)
            self.assertNotIn(key, s.parse_config(candidate)["model_providers"][s.DEFAULT_PROVIDER])

    def test_linux_apply_verify_restore_roundtrip(self):
        before, _ = self.fixture_state()
        s.atomic_write(self.home / "nylohq-lb/api-key.pending", b"fixture-key")
        with patch.object(s.platform, "system", return_value="Linux"), patch.object(s, "find_cli", return_value=("fixture-cli", "0.171.0")), patch.object(s, "fetch_catalog", return_value=catalog()), patch.object(s, "strict_check"), patch.object(s, "smoke_check"), contextlib.redirect_stdout(io.StringIO()):
            s.apply(self.home, transport="sse", text_only=True)
            self.assertFalse((self.home / "nylohq-lb/api-key.pending").exists())
            self.assertEqual((self.home / "nylohq-lb/api-key").read_bytes(), b"fixture-key")
            s.verify(self.home)
            backup = next((self.home / "backups").glob("nylohq-setup-*"))
            s.restore(self.home, backup)
        for name in s.TARGETS:
            self.assertEqual(s.read_optional(self.home / name), before[name])

    @unittest.skipUnless(os.environ.get("NYLOHQ_TEST_CODEX"), "Optional official CLI strict-config test")
    def test_official_cli_accepts_generated_transport_configs_offline(self):
        # No real config/key/catalog, auth command execution or provider request.
        selected = os.environ["NYLOHQ_TEST_CODEX"]
        cli, _ = s.find_cli(None if selected == "auto" else selected)
        for transport in ("sse", "websocket"):
            with self.subTest(transport=transport):
                candidate, _ = s.build_config(None, self.home, "gpt-6-luna", "high", transport=transport, text_only=True)
                s.strict_check(cli, candidate, json.dumps(catalog()).encode(), self.home)

    def test_backup_and_exact_restore(self):
        before, after = self.fixture_state()
        backup = s.commit(self.home, before, after)
        for name in s.TARGETS:
            self.assertEqual(s.read_optional(self.home / name), after[name])
        with patch.object(s, "native_os", return_value="Darwin"), contextlib.redirect_stdout(io.StringIO()):
            s.restore(self.home, backup)
        for name in s.TARGETS:
            self.assertEqual(s.read_optional(self.home / name), before[name])
        self.assertEqual(json.loads((backup / "manifest.json").read_text())["status"], "restored")

    def test_restore_removes_files_that_did_not_exist(self):
        before = {name: None for name in s.TARGETS}
        after = {"config.toml": self.config(None), "nylohq-lb/api-key": b"fixture", "nylohq-lb/models.json": b"{}"}
        backup = s.commit(self.home, before, after)
        with patch.object(s, "native_os", return_value="Darwin"), contextlib.redirect_stdout(io.StringIO()):
            s.restore(self.home, backup)
        self.assertTrue(all(not (self.home / name).exists() for name in s.TARGETS))

    def test_restore_refuses_later_edits(self):
        before, after = self.fixture_state()
        backup = s.commit(self.home, before, after)
        changed = after["config.toml"] + b"\n# later member edit\n"
        s.atomic_write(self.home / "config.toml", changed)
        with patch.object(s, "native_os", return_value="Darwin"), self.assertRaises(s.SetupError):
            s.restore(self.home, backup)
        self.assertEqual((self.home / "config.toml").read_bytes(), changed)
        self.assertEqual((self.home / "nylohq-lb/api-key").read_bytes(), after["nylohq-lb/api-key"])

    def test_corrupt_backup_stops(self):
        before, after = self.fixture_state()
        backup = s.commit(self.home, before, after)
        (backup / "0.before").write_bytes(b"corrupted")
        with patch.object(s, "native_os", return_value="Darwin"), self.assertRaises(s.SetupError):
            s.restore(self.home, backup)
        self.assertEqual((self.home / "config.toml").read_bytes(), after["config.toml"])

    def test_changed_file_before_commit_stops(self):
        before, after = self.fixture_state()
        (self.home / "config.toml").write_bytes(b"# external edit\n")
        with self.assertRaises(s.SetupError):
            s.commit(self.home, before, after)
        self.assertFalse((self.home / "backups").exists())

    def test_mid_commit_error_rolls_back(self):
        before, after = self.fixture_state()
        actual = s.atomic_write
        failed = False
        def fail_once(path, data):
            nonlocal failed
            if path == self.home / "config.toml" and not failed:
                failed = True
                raise OSError("fixture failure")
            actual(path, data)
        with patch.object(s, "atomic_write", side_effect=fail_once), self.assertRaises(s.SetupError):
            s.commit(self.home, before, after)
        for name in s.TARGETS:
            self.assertEqual(s.read_optional(self.home / name), before[name])

    def test_restore_recovers_interrupted_prepared_commit(self):
        before, after = self.fixture_state()
        backup, _ = s.snapshot(self.home, before, after)
        s.atomic_write(self.home / "nylohq-lb/api-key", after["nylohq-lb/api-key"])
        with patch.object(s, "native_os", return_value="Darwin"), contextlib.redirect_stdout(io.StringIO()):
            s.restore(self.home, backup)
        for name in s.TARGETS:
            self.assertEqual(s.read_optional(self.home / name), before[name])

    def test_private_permissions(self):
        if os.name == "nt":
            self.skipTest("POSIX mode check; Windows uses the separate DACL test")
        before, after = self.fixture_state()
        backup = s.commit(self.home, before, after)
        self.assertEqual((self.home / "nylohq-lb").stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.home / "nylohq-lb/api-key").stat().st_mode & 0o777, 0o600)
        self.assertEqual(backup.stat().st_mode & 0o777, 0o700)
        self.assertEqual((backup / "0.before").stat().st_mode & 0o777, 0o600)

    @unittest.skipUnless(os.name == "nt", "Native Windows DACL check")
    def test_windows_private_dacl(self):
        path = self.home / "nylohq-lb/api-key"
        s.atomic_write(path, b"fixture-key")
        for target, kind in ((path, "File"), (path.parent, "Directory")):
            script = (
                "$ErrorActionPreference='Stop';"
                "$sid=[System.Security.Principal.WindowsIdentity]::GetCurrent().User;"
                f"$acl=[System.IO.{kind}]::GetAccessControl({s.ps_quote(target)});"
                "$rules=$acl.GetAccessRules($true,$true,[System.Security.Principal.SecurityIdentifier]);"
                "if(-not $acl.AreAccessRulesProtected -or $rules.Count -ne 1 "
                "-or $rules[0].IdentityReference.Value -ne $sid.Value "
                "-or $rules[0].IsInherited -or $rules[0].AccessControlType -ne 'Allow' "
                "-or $rules[0].FileSystemRights -ne 'FullControl'){exit 1}"
            )
            result = s.subprocess.run([s.powershell(), "-NoProfile", "-NonInteractive", "-Command", script], capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))

    def test_redirect_never_forwards_credentials(self):
        with self.assertRaises(s.SetupError):
            s.NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.invalid")

    def test_invalid_toml_error_does_not_echo_source(self):
        with self.assertRaises(s.SetupError) as error:
            s.parse_config(b'key = "fixture-secret" INVALID')
        self.assertNotIn("fixture-secret", str(error.exception))

    def test_noninteractive_key_entry_stops(self):
        with patch.object(s, "native_os", return_value="Darwin"), patch.object(s.sys.stdin, "isatty", return_value=False), patch.object(s.getpass, "getpass") as ask:
            with self.assertRaises(s.SetupError):
                s.enter_key(self.home)
            ask.assert_not_called()

    def test_bad_key_not_returned_in_error(self):
        path = self.home / "nylohq-lb/api-key.pending"
        path.write_bytes(b"fixture-secret\nheader-injection")
        with self.assertRaises(s.SetupError) as error:
            s.read_key(path)
        self.assertNotIn("fixture-secret", str(error.exception))

    def test_lock_is_exclusive_and_released(self):
        with s.setup_lock(self.home):
            with self.assertRaises(s.SetupError):
                with s.setup_lock(self.home):
                    pass
        self.assertFalse((self.home / "nylohq-lb/setup.lock").exists())

    def test_symlink_target_refused(self):
        if os.name == "nt":
            self.skipTest("Symlink creation may require Windows developer mode")
        target = self.home / "untouched"
        target.write_text("original")
        link = self.home / "config.toml"
        link.symlink_to(target)
        with self.assertRaises(s.SetupError):
            s.atomic_write(link, b"changed")
        self.assertEqual(target.read_text(), "original")

    def test_catalog_failure_does_not_commit_config(self):
        before, _ = self.fixture_state()
        s.atomic_write(self.home / "nylohq-lb/api-key.pending", b"fixture-key")
        with patch.object(s, "native_os", return_value="Darwin"), patch.object(s, "find_cli", return_value=("fake-codex", "0.164.0")), patch.object(s, "fetch_catalog", side_effect=s.SetupError("HTTP 401")):
            with self.assertRaises(s.SetupError):
                s.apply(self.home)
        for name in s.TARGETS:
            self.assertEqual(s.read_optional(self.home / name), before[name])
        self.assertFalse((self.home / "backups").exists())

    def test_smoke_failure_does_not_commit_config(self):
        before, _ = self.fixture_state()
        s.atomic_write(self.home / "nylohq-lb/api-key.pending", b"fixture-key")
        with patch.object(s, "native_os", return_value="Darwin"), patch.object(s, "find_cli", return_value=("fake-codex", "0.164.0")), patch.object(s, "fetch_catalog", return_value=catalog()), patch.object(s, "strict_check"), patch.object(s, "smoke_check", side_effect=s.SetupError("text failed")), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(s.SetupError):
                s.apply(self.home)
        for name in s.TARGETS:
            self.assertEqual(s.read_optional(self.home / name), before[name])
        self.assertFalse((self.home / "backups").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
