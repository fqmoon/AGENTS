"""Regression checks for per-number default fragment selection."""

from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("gen-agents-md.py")
resolve = runpy.run_path(str(SCRIPT))["resolve"]


class DefaultSelectionTests(unittest.TestCase):
    def test_defaults_are_scoped_to_each_number(self):
        groups = {
            "010": [("default", Path("010-default.md"))],
            "030": [
                ("cline", Path("030-cline.md")),
                ("default", Path("030-default.md")),
                ("gpt", Path("030-gpt.md")),
            ],
            "050": [
                ("default", Path("050-default.md")),
                ("wsl2", Path("050-wsl2.md")),
            ],
        }
        chosen, errors = resolve(groups, ["gpt"])
        self.assertEqual(errors, [])
        self.assertEqual(list(chosen.values()), [
            Path("010-default.md"),
            Path("030-gpt.md"),
            Path("050-default.md"),
        ])

    def test_single_file_still_joins_automatically(self):
        chosen, errors = resolve({"020": [("subagent", Path("020-subagent.md"))]}, [])
        self.assertEqual(errors, [])
        self.assertEqual(chosen, {"020": Path("020-subagent.md")})

    def test_another_groups_default_does_not_make_selection_optional(self):
        chosen, errors = resolve({
            "010": [("default", Path("010-default.md"))],
            "050": [
                ("windows", Path("050-windows.md")),
                ("wsl2", Path("050-wsl2.md")),
            ],
        }, [])
        self.assertNotIn("050", chosen)
        self.assertEqual(len(errors), 1)
        self.assertIn("number 050", errors[0])
        self.assertIn("select one", errors[0])

    def test_default_does_not_allow_multiple_explicit_selections(self):
        chosen, errors = resolve({"030": [
            ("cline", Path("030-cline.md")),
            ("default", Path("030-default.md")),
            ("gpt", Path("030-gpt.md")),
        ]}, ["gpt", "cline"])
        self.assertNotIn("030", chosen)
        self.assertEqual(len(errors), 1)
        self.assertIn("2 selections", errors[0])

    def test_default_is_reserved_for_automatic_fallback(self):
        _, errors = resolve({"010": [("default", Path("010-default.md"))]}, ["default"])
        self.assertEqual(len(errors), 1)
        self.assertIn("reserved", errors[0])

    def test_cli_with_empty_default_override_and_invalid_selection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = root / SCRIPT.name
            shutil.copyfile(SCRIPT, script)
            for name, text in {
                "010-default.md": "Common rules\n",
                "030-default.md": "",
                "030-gpt.md": "GPT rules\n",
                "030-cline.md": "Cline rules\n",
                "040-tools.md": "Tools\n",
            }.items():
                (root / name).write_text(text, encoding="utf-8")
            output = root / "output"
            command = [sys.executable, str(script), str(output)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            target = output / "AGENTS.md"
            text = target.read_text(encoding="utf-8")
            self.assertEqual(text.split(), ["Common", "rules", "Tools"])
            self.assertIn("030-default.md", result.stdout)

            result = subprocess.run(command + ["-s", "gpt"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            text = target.read_text(encoding="utf-8")
            self.assertEqual(text, "Common rules\n\nGPT rules\n\nTools\n")
            self.assertNotIn("030-default.md", result.stdout)

            result = subprocess.run(command + ["-s", "missing"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("unknown selection", result.stderr)
            self.assertEqual(target.read_text(encoding="utf-8"), text)


if __name__ == "__main__":
    unittest.main()
