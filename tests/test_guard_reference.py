"""Exercise boundary tests with temporary public and protected documents."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "guard_reference.py"


class ReferenceGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("guard_reference", SCRIPT)
        if spec is None or spec.loader is None:
            raise RuntimeError("The guard module could not be loaded.")
        cls.guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.guard)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        files = (
            "AGENTS.md",
            "CLAUDE.md",
            "README.md",
            "docs/start.md",
            "exercises/01-documents/task.md",
            "exercises/01-documents/README.md",
            "exercises/01-documents/inputs/faq.md",
            "exercises/01-documents/inputs.sha256.json",
            "exercises/01-documents/answer.md",
            "tools/check_answer.py",
            "tools/guard_reference.py",
            "tests/test_sample.py",
            "examples/hook/settings.json",
            "_reference/hidden.md",
            ".git/config",
            ".claude/settings.json",
        )
        for name in files:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Synthetic test fixture.\n", encoding="utf-8")
        self.exercise = "exercises/01-documents"

    def event(self, tool, tool_input, cwd=None):
        return {
            "hook_event_name": "PreToolUse",
            "tool_name": tool,
            "tool_input": tool_input,
            "cwd": str(cwd or self.root),
        }

    def assert_allowed(self, tool, tool_input, cwd=None):
        result = self.guard.decision(self.event(tool, tool_input, cwd), self.root)
        self.assertEqual(result, {}, result)

    def assert_denied(self, tool, tool_input, cwd=None):
        result = self.guard.decision(self.event(tool, tool_input, cwd), self.root)
        output = result["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "PreToolUse")
        self.assertEqual(output["permissionDecision"], "deny")
        self.assertTrue(output["permissionDecisionReason"])
        return result

    def symlink(self, link, target):
        try:
            link.symlink_to(target, target_is_directory=target.is_dir())
        except OSError as error:
            self.skipTest(f"Symbolic links unavailable: {error}")

    def test_public_files_can_be_read(self):
        for name in (
            "AGENTS.md",
            "CLAUDE.md",
            "README.md",
            "docs/start.md",
            self.exercise + "/task.md",
            self.exercise + "/README.md",
            self.exercise + "/inputs/faq.md",
            self.exercise + "/inputs.sha256.json",
            "tools/check_answer.py",
            "tests/test_sample.py",
            "examples/hook/settings.json",
        ):
            with self.subTest(name=name):
                self.assert_allowed("Read", {"file_path": name})

    def test_private_or_external_read_is_denied(self):
        for name in (
            "_reference/hidden.md",
            "docs/../_reference/hidden.md",
            "_REFERENCE/hidden.md",
            "_reference\\hidden.md",
            ".git/config",
            ".claude/settings.json",
            "../foreign.md",
            "/etc/passwd",
        ):
            with self.subTest(name=name):
                self.assert_denied("Read", {"file_path": name})

    def test_canonical_root_accepts_repository_cwd_through_symlink_alias(self):
        aliases = self.root / "aliases"
        aliases.mkdir()
        alias = aliases / "repo"
        self.symlink(alias, self.root)
        event = self.event("Read", {"file_path": "README.md"}, alias)
        self.assertEqual(self.guard.decision(event, self.root.resolve()), {})
        event = self.event(
            "Read", {"file_path": str(alias / "docs" / "start.md")}, alias
        )
        self.assertEqual(self.guard.decision(event, self.root.resolve()), {})

    def test_repository_alias_does_not_open_protected_files(self):
        alias = self.root / "repo-alias"
        self.symlink(alias, self.root)
        event = self.event(
            "Read", {"file_path": str(alias / "_reference" / "hidden.md")}, alias
        )
        output = self.guard.decision(event, self.root.resolve())["hookSpecificOutput"]
        self.assertEqual(output["permissionDecision"], "deny")

    def test_read_path_fallback_and_nested_cwd(self):
        self.assert_allowed(
            "Read", {"path": "faq.md"}, self.root / self.exercise / "inputs"
        )

    def test_read_through_symlink_to_protected_file_is_denied(self):
        self.symlink(
            self.root / "docs" / "shortcut.md", self.root / "_reference" / "hidden.md"
        )
        self.assert_denied("Read", {"file_path": "docs/shortcut.md"})

    def test_parent_component_after_symlink_cannot_hide_reference_target(self):
        nested = self.root / "_reference" / "nested"
        nested.mkdir()
        self.symlink(self.root / "docs" / "shortcut", nested)
        self.assert_denied("Read", {"file_path": "docs/shortcut/../hidden.md"})
        self.assert_denied(
            "Grep", {"path": "docs/shortcut/../hidden.md", "pattern": "fixture"}
        )

    def test_read_through_symlink_outside_repository_is_denied(self):
        self.symlink(self.root / "docs" / "outside", self.root.parent)
        self.assert_denied("Read", {"file_path": "docs/outside/foreign.md"})

    def test_symlink_loop_fails_closed_without_exception(self):
        first = self.root / "docs" / "first-loop"
        second = self.root / "docs" / "second-loop"
        self.symlink(first, second)
        self.symlink(second, first)
        self.assert_denied("Read", {"file_path": "docs/first-loop"})
        self.assert_denied("Bash", {"command": "cat docs/first-loop"})

    def test_read_root_directory_is_denied(self):
        self.assert_denied("Read", {"file_path": "."})

    def test_result_markdown_can_be_written_and_read(self):
        for name in ("answer.md", "my-prompt.md", "notes.md", "attempts/second.md"):
            with self.subTest(name=name):
                self.assert_allowed(
                    "Write",
                    {
                        "file_path": self.exercise + "/" + name,
                        "content": "_reference is just a string",
                    },
                )
                self.assert_allowed("Read", {"file_path": self.exercise + "/" + name})

    def test_reference_in_written_content_does_not_restrict_result_path(self):
        self.assert_allowed(
            "Edit",
            {
                "file_path": self.exercise + "/answer.md",
                "new_string": "Read _reference/hidden.md",
            },
        )

    def test_protected_files_cannot_be_written_or_edited(self):
        for tool in ("Write", "Edit"):
            for name in (
                "README.md",
                "AGENTS.md",
                "CLAUDE.md",
                "docs/start.md",
                "tools/check_answer.py",
                "tests/test_sample.py",
                ".claude/settings.json",
                self.exercise + "/task.md",
                self.exercise + "/README.md",
                self.exercise + "/inputs.sha256.json",
                self.exercise + "/inputs/faq.md",
                self.exercise + "/attempts/script.py",
                "_reference/hidden.md",
            ):
                with self.subTest(tool=tool, name=name):
                    self.assert_denied(tool, {"file_path": name})

    def test_result_symlink_cannot_be_used_to_overwrite_reference(self):
        path = self.root / self.exercise / "answer.md"
        path.unlink()
        self.symlink(path, self.root / "_reference" / "hidden.md")
        self.assert_denied("Write", {"file_path": self.exercise + "/answer.md"})

    def test_glob_can_search_explicit_public_directory(self):
        self.assert_allowed("Glob", {"path": "docs", "pattern": "**/*.md"})
        self.assert_allowed("Glob", {"path": ".", "pattern": "docs/**/*.md"})
        self.assert_allowed("Glob", {"path": ".", "pattern": "README.md"})

    def test_glob_cannot_search_root_or_reference(self):
        for arguments in (
            {"path": ".", "pattern": "**/*.md"},
            {"pattern": "**"},
            {"path": "_reference", "pattern": "*.md"},
            {"path": "docs", "pattern": "../_reference/*.md"},
        ):
            with self.subTest(arguments=arguments):
                self.assert_denied("Glob", arguments)

    def test_grep_requires_explicit_public_scope(self):
        self.assert_allowed("Grep", {"path": "docs", "pattern": "fixture"})
        self.assert_allowed(
            "Grep", {"path": self.exercise + "/inputs/faq.md", "pattern": "fixture"}
        )
        self.assert_denied(
            "Grep", {"path": ".", "pattern": "fixture", "glob": "docs/*.md"}
        )
        self.assert_denied("Grep", {"pattern": "fixture"})
        self.assert_denied("Grep", {"path": "_reference", "pattern": "fixture"})

    def test_recursive_search_rejects_public_scope_with_protected_symlink(self):
        self.symlink(self.root / "docs" / "hidden-link", self.root / "_reference")
        self.assert_denied("Grep", {"path": "docs", "pattern": "fixture"})
        self.assert_denied("Glob", {"path": "docs", "pattern": "**/*.md"})

    def test_grep_glob_cannot_escape_scope(self):
        self.assert_denied(
            "Grep",
            {"path": "docs", "pattern": "fixture", "glob": "../../_reference/**"},
        )

    def test_simple_shell_reads_are_allowed(self):
        for command in (
            "pwd",
            "ls",
            "ls .",
            "ls -la",
            "dir",
            "ls docs",
            "cat README.md",
            "cat docs/start.md AGENTS.md",
            "Get-Content docs/start.md",
            "Get-Content -LiteralPath docs/start.md",
            "rg --files docs",
            "rg fixture docs",
            'rg "test fixture" docs/start.md',
        ):
            with self.subTest(command=command):
                self.assert_allowed("Bash", {"command": command})

    def test_shell_cmd_fallback_is_supported(self):
        self.assert_allowed("Bash", {"cmd": "cat README.md"})

    def test_shell_paths_resolve_from_nested_cwd(self):
        self.assert_allowed(
            "Bash", {"command": "cat faq.md"}, self.root / self.exercise / "inputs"
        )

    def test_shell_workdir_cannot_escape_repository(self):
        self.assert_denied(
            "Bash", {"command": "cat README.md", "workdir": str(self.root.parent)}
        )

    def test_unrestricted_commands_and_compound_shell_are_denied(self):
        for command in (
            "cat _reference/hidden.md",
            "cat .git/config",
            "ls _reference",
            "ls -R .",
            "rg --files",
            "rg fixture .",
            "rg --files .",
            "rg --pre docs",
            "python -c 'print(1)'",
            "python3 script.py",
            "node script.js",
            "curl https://example.com",
            "git show HEAD:README.md",
            "pwd; cat _reference/hidden.md",
            "pwd && ls",
            "pwd | cat",
            "pwd\nls",
            "cat < README.md",
            "pwd > result.md",
            "echo $(pwd)",
            "echo `pwd`",
            "bash -c pwd",
        ):
            with self.subTest(command=command):
                self.assert_denied("Bash", {"command": command})

    def test_shell_cannot_override_interpreter_or_environment(self):
        for override in (
            {"shell": "python"},
            {"env": {"BASH_ENV": "_reference/hidden.md"}},
            {"stdin": "arbitrary code"},
        ):
            with self.subTest(override=override):
                self.assert_denied("Bash", {"command": "pwd", **override})

    def test_ambiguous_path_or_command_fields_are_denied(self):
        self.assert_denied(
            "Read", {"file_path": "README.md", "path": "_reference/hidden.md"}
        )
        self.assert_denied(
            "Bash", {"command": "pwd", "cmd": "cat _reference/hidden.md"}
        )

    def test_shell_cat_requires_explicit_files_without_globs(self):
        self.assert_denied("Bash", {"command": "cat docs/*"})
        self.assert_denied("Bash", {"command": "cat docs"})

    def test_trusted_checker_with_isolated_python_is_allowed(self):
        for interpreter in ("python", "python3", "py", "py -3"):
            with self.subTest(interpreter=interpreter):
                self.assert_allowed(
                    "Bash",
                    {
                        "command": interpreter
                        + " -I tools/check_answer.py "
                        + self.exercise
                        + "/answer.md"
                    },
                )

    def test_checker_requires_isolation_and_exact_script(self):
        for command in (
            "python tools/check_answer.py " + self.exercise + "/answer.md",
            "python -I docs/check_answer.py " + self.exercise + "/answer.md",
            "python -I tools/check_answer.py --hook",
            "python -I tools/check_answer.py " + self.exercise + "/answer.md --other",
            "python -I tools/check_answer.py _reference/hidden.md",
        ):
            with self.subTest(command=command):
                self.assert_denied("Bash", {"command": command})

    def test_checker_script_symlink_is_not_trusted(self):
        path = self.root / "tools" / "check_answer.py"
        path.unlink()
        self.symlink(path, self.root / "_reference" / "hidden.md")
        self.assert_denied(
            "Bash",
            {
                "command": "python -I tools/check_answer.py "
                + self.exercise
                + "/answer.md"
            },
        )

    def test_patch_can_add_update_move_or_delete_result_markdown(self):
        prefix = "*** Begin Patch\n"
        suffix = "\n*** End Patch"
        patches = (
            "*** Add File: " + self.exercise + "/my-prompt.md\n+some prompt",
            "*** Update File: " + self.exercise + "/answer.md\n@@\n-old\n+new",
            "*** Delete File: " + self.exercise + "/notes.md",
            "*** Update File: "
            + self.exercise
            + "/answer.md\n*** Move to: "
            + self.exercise
            + "/attempts/first.md\n@@\n-old\n+new",
        )
        for patch in patches:
            with self.subTest(patch=patch):
                self.assert_allowed("apply_patch", {"command": prefix + patch + suffix})

    def test_patch_content_is_not_interpreted_as_target_paths(self):
        patch = (
            "*** Begin Patch\n*** Add File: "
            + self.exercise
            + "/notes.md\n+*** Update File: _reference/hidden.md\n+cat .git/config\n*** End Patch"
        )
        self.assert_allowed("apply_patch", {"command": patch})

    def test_patch_cannot_change_or_move_into_protected_paths(self):
        for patch in (
            "*** Add File: tools/exploit.py\n+bad",
            "*** Update File: " + self.exercise + "/inputs/faq.md\n@@\n-old\n+new",
            "*** Delete File: _reference/hidden.md",
            "*** Update File: "
            + self.exercise
            + "/answer.md\n*** Move to: .claude/settings.json\n@@\n-old\n+new",
            "*** Add File: ../outside.md\n+bad",
        ):
            with self.subTest(patch=patch):
                self.assert_denied(
                    "apply_patch",
                    {"command": "*** Begin Patch\n" + patch + "\n*** End Patch"},
                )

    def test_malformed_or_headerless_patch_is_denied(self):
        for patch in (
            "echo hello",
            "*** Begin Patch\n*** End Patch",
            "*** Begin Patch\n*** Add File:\n+bad\n*** End Patch",
        ):
            with self.subTest(patch=patch):
                self.assert_denied("apply_patch", {"command": patch})

    def test_unknown_tools_and_remote_execution_are_denied(self):
        for tool in (
            "Agent",
            "Task",
            "WebFetch",
            "WebSearch",
            "mcp__files__read",
            "PowerShell",
            "exec_command",
            "Unknown",
        ):
            with self.subTest(tool=tool):
                self.assert_denied(tool, {"command": "pwd"})

    def test_metadata_tools_and_empty_poll_are_allowed(self):
        self.assert_allowed("update_plan", {"plan": []})
        self.assert_allowed("AskUserQuestion", {"questions": []})
        self.assert_allowed("write_stdin", {"session_id": 1})
        self.assert_allowed("write_stdin", {"session_id": 1, "chars": ""})

    def test_session_input_is_denied(self):
        self.assert_denied(
            "write_stdin", {"session_id": 1, "chars": "cat _reference/hidden.md\n"}
        )

    def test_malformed_or_wrong_events_fail_closed(self):
        for event in (
            None,
            [],
            {},
            {"hook_event_name": "Stop"},
            self.event("Read", "bad input"),
            self.event("Read", {"file_path": 12}),
        ):
            with self.subTest(event=event):
                output = self.guard.decision(event, self.root)["hookSpecificOutput"]
                self.assertEqual(output["permissionDecision"], "deny")

    def test_cli_malformed_json_returns_deny_without_traceback(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input="not json",
            text=True,
            capture_output=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(output["permissionDecision"], "deny")


if __name__ == "__main__":
    unittest.main()
