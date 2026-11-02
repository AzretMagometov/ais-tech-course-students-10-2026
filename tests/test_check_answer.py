"""Behavioral tests using invented documents and temporary exercise folders."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "check_answer.py"
QUOTE = "Учебный маяк включают только после проверки кабеля."
SOURCE = (
    "# Учебная памятка\n\n## Подготовка\n\n"
    + QUOTE
    + "\n\n## Другая тема\n\nЗдесь другая строка.\n"
)
ANSWER = """# Результат

## Ответ

Вывод участника проверяется вручную.

## Точная цитата

> {quote}

## Источник

Файл: inputs/manual.md
Раздел: Подготовка

## Проверка и ограничения

Наличие цитаты проверено отдельно от смысла вывода.
""".format(quote=QUOTE)


class AnswerCheckerTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.exercise = self.root / "exercises" / "01-documents"
        self.inputs = self.exercise / "inputs"
        self.inputs.mkdir(parents=True)
        self.source = self.inputs / "manual.md"
        self.source.write_text(SOURCE, encoding="utf-8")
        self.manifest = self.exercise / "inputs.sha256.json"
        self.write_manifest()
        self.answer = self.exercise / "answer.md"
        self.answer.write_text(ANSWER, encoding="utf-8")

    def write_manifest(self):
        files = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in self.inputs.iterdir()
            if path.is_file()
        }
        self.manifest.write_text(json.dumps(files), encoding="utf-8")

    def invoke(self, *arguments, payload=None):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *arguments],
            cwd=self.root,
            input=json.dumps(payload) if isinstance(payload, dict) else payload,
            text=True,
            capture_output=True,
            encoding="utf-8",
        )

    def check(self, expected_code=0):
        result = self.invoke(str(self.answer))
        self.assertEqual(
            result.returncode, expected_code, result.stdout + result.stderr
        )
        self.assertNotIn("Traceback", result.stderr)
        return result.stdout + result.stderr

    def hook(self, **overrides):
        event = {
            "hook_event_name": "Stop",
            "cwd": str(self.root),
            "stop_hook_active": False,
        }
        event.update(overrides)
        result = self.invoke("--hook", payload=event)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        return json.loads(result.stdout)

    def test_valid_answer_passes_and_states_manual_limit(self):
        message = self.check()
        self.assertIn("вручную", message)

    def test_default_answer_path_works_from_repository_root(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_answer_claim_is_not_treated_as_semantically_verified(self):
        self.answer.write_text(
            ANSWER.replace(
                "Вывод участника проверяется вручную.", "Любое выдуманное утверждение."
            ),
            encoding="utf-8",
        )
        self.assertIn("вручную", self.check())

    def test_missing_answer_fails(self):
        self.answer.unlink()
        self.assertIn("answer.md", self.check(1))

    def test_missing_required_section_fails(self):
        self.answer.write_text(
            ANSWER.replace("## Проверка и ограничения", "## Иное"), encoding="utf-8"
        )
        self.assertIn("Проверка и ограничения", self.check(1))

    def test_empty_required_section_fails(self):
        self.answer.write_text(
            ANSWER.replace("Вывод участника проверяется вручную.", ""), encoding="utf-8"
        )
        self.assertIn("Ответ", self.check(1))

    def test_duplicate_answer_heading_fails(self):
        self.answer.write_text(ANSWER + "\n## Ответ\nДругой ответ.\n", encoding="utf-8")
        self.assertIn("повтор", self.check(1).lower())

    def test_fake_sections_inside_fenced_code_do_not_pass(self):
        self.answer.write_text("```markdown\n" + ANSWER + "\n```\n", encoding="utf-8")
        self.check(1)

    def test_quote_must_be_a_blockquote(self):
        self.answer.write_text(ANSWER.replace("> " + QUOTE, QUOTE), encoding="utf-8")
        self.assertIn("цитат", self.check(1).lower())

    def test_changed_quote_fails(self):
        self.answer.write_text(
            ANSWER.replace(QUOTE, "Выдуманная строка без источника."), encoding="utf-8"
        )
        self.assertIn("цитат", self.check(1).lower())

    def test_quote_must_come_from_the_named_section(self):
        self.answer.write_text(
            ANSWER.replace("Раздел: Подготовка", "Раздел: Другая тема"),
            encoding="utf-8",
        )
        self.check(1)

    def test_unknown_section_fails(self):
        self.answer.write_text(
            ANSWER.replace("Раздел: Подготовка", "Раздел: Несуществующий"),
            encoding="utf-8",
        )
        self.assertIn("раздел", self.check(1).lower())

    def test_source_fields_can_use_inline_code(self):
        self.answer.write_text(
            ANSWER.replace("Файл: inputs/manual.md", "Файл: `inputs/manual.md`"),
            encoding="utf-8",
        )
        self.check()

    def test_missing_source_file_field_fails(self):
        self.answer.write_text(
            ANSWER.replace("Файл: inputs/manual.md", "Документ неизвестен"),
            encoding="utf-8",
        )
        self.assertIn("Файл", self.check(1))

    def test_parent_traversal_fails(self):
        outside = self.exercise / "outside.md"
        outside.write_text(SOURCE, encoding="utf-8")
        self.answer.write_text(
            ANSWER.replace("inputs/manual.md", "inputs/../outside.md"), encoding="utf-8"
        )
        self.check(1)

    def test_absolute_source_path_fails(self):
        self.answer.write_text(
            ANSWER.replace("inputs/manual.md", str(self.source)), encoding="utf-8"
        )
        self.check(1)

    def test_external_symlink_fails(self):
        outside = self.root / "outside.md"
        outside.write_text(SOURCE, encoding="utf-8")
        self.source.unlink()
        try:
            self.source.symlink_to(outside)
        except OSError as error:
            self.skipTest(f"Symbolic links are unavailable: {error}")
        self.check(1)

    def test_changed_source_hash_fails(self):
        self.source.write_text(SOURCE + "Изменено.\n", encoding="utf-8")
        self.assertIn("измен", self.check(1).lower())

    def test_added_source_file_fails(self):
        (self.inputs / "extra.md").write_text(
            "Дополнительный документ", encoding="utf-8"
        )
        self.check(1)

    def test_removed_source_file_fails(self):
        self.source.unlink()
        self.check(1)

    def test_malformed_manifest_fails_without_traceback(self):
        self.manifest.write_text("not json", encoding="utf-8")
        self.check(1)

    def test_invalid_manifest_shape_fails_without_traceback(self):
        self.manifest.write_text("[]", encoding="utf-8")
        self.check(1)

    def test_invalid_utf8_answer_fails_without_traceback(self):
        self.answer.write_bytes(b"\xff")
        self.check(1)

    def test_invalid_utf8_source_fails_without_traceback(self):
        self.source.write_bytes(b"\xff")
        self.write_manifest()
        self.check(1)

    def test_successful_hook_returns_empty_object(self):
        self.assertEqual(self.hook(), {})

    def test_hook_finds_repository_from_nested_cwd(self):
        self.assertEqual(self.hook(cwd=str(self.inputs)), {})

    def test_hook_does_not_accept_foreign_parent_without_manifest(self):
        other = self.root / "unrelated"
        other.mkdir()
        self.manifest.unlink()
        self.assertEqual(self.hook(cwd=str(other))["decision"], "block")

    def test_hook_rejects_non_object_json(self):
        result = self.invoke("--hook", payload="[]")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["decision"], "block")

    def test_hook_rejects_other_event(self):
        self.assertEqual(self.hook(hook_event_name="PreToolUse")["decision"], "block")

    def test_first_hook_failure_blocks_with_reason(self):
        self.answer.unlink()
        result = self.hook()
        self.assertEqual(result["decision"], "block")
        self.assertIn("answer.md", result["reason"])

    def test_repeated_hook_failure_warns_without_looping(self):
        self.answer.unlink()
        result = self.hook(stop_hook_active=True)
        self.assertNotIn("decision", result)
        self.assertIn("systemMessage", result)

    def test_malformed_hook_json_has_diagnostic_not_traceback(self):
        result = self.invoke("--hook", payload="not json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["decision"], "block")
        self.assertNotIn("Traceback", result.stderr)

    def test_invalid_hook_cwd_is_rejected(self):
        self.assertEqual(self.hook(cwd=None)["decision"], "block")

    def test_unknown_cli_argument_is_a_usage_error(self):
        result = self.invoke("--does-not-exist")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
