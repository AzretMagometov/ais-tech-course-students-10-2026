"""Restrict first-exercise agent tools without treating hooks as an OS sandbox."""

import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import sys


EXERCISE = Path("exercises") / "01-documents"
PRIVATE_PARTS = frozenset({"_reference", ".git", ".claude"})
ROOT_DOCUMENTS = frozenset({"agents.md", "claude.md", "readme.md"})
PUBLIC_DIRECTORIES = frozenset({"docs", "tools", "tests", "examples"})
RESULT_FILES = frozenset({"answer.md", "my-prompt.md", "notes.md"})
METADATA_TOOLS = frozenset(
    {"update_plan", "AskUserQuestion", "request_user_input", "TodoWrite"}
)
SHELL_META = frozenset(";&|><$`\n\r\x00(){}")
GLOB_CHARACTERS = frozenset("*?[]{}")


class Denied(ValueError):
    """A policy diagnostic that never contains protected document contents."""


def deny(reason: str) -> dict[str, object]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


class Policy:
    """Resolve every path before applying the exercise's narrow access rules."""

    def __init__(self, root: Path, cwd: object):
        self.root = root.resolve()
        self.lexical_root = Path(os.path.abspath(root))
        self.cwd = self.root
        if not isinstance(cwd, str) or not Path(cwd.replace("\\", "/")).is_absolute():
            raise Denied("В событии нужен абсолютный путь cwd к учебному репозиторию.")
        self.set_cwd(self.path(cwd))

    def path(self, raw: object, base: Path | None = None) -> Path:
        if not isinstance(raw, str) or not raw or "\x00" in raw:
            raise Denied("Нужен явный путь к публичному файлу или папке упражнения.")
        normalized = raw.replace("\\", "/")
        candidate = Path(normalized)
        if not candidate.is_absolute():
            candidate = (base or self.cwd) / candidate
        lexical = Path(os.path.abspath(candidate))
        relative = None
        for alias in (self.root, self.lexical_root):
            try:
                relative = lexical.relative_to(alias)
                break
            except ValueError:
                continue
        lexical_parts = relative.parts if relative is not None else lexical.parts
        if any(part.casefold() in PRIVATE_PARTS for part in lexical_parts):
            raise Denied(
                "Служебные каталоги и эталон недоступны агенту в этом упражнении."
            )
        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError:
            resolved = candidate.resolve()
        try:
            relative = resolved.relative_to(self.root)
        except ValueError as error:
            raise Denied(
                "Символическая ссылка ведёт за пределы учебного репозитория."
            ) from error
        if any(part.casefold() in PRIVATE_PARTS for part in relative.parts):
            raise Denied("Символическая ссылка ведёт в закрытый каталог.")
        return resolved

    def relative_parts(self, path: Path) -> tuple[str, ...]:
        return tuple(part.casefold() for part in path.relative_to(self.root).parts)

    def writable(self, path: Path) -> bool:
        parts = self.relative_parts(path)
        if parts[:2] != ("exercises", "01-documents"):
            return False
        rest = parts[2:]
        return (len(rest) == 1 and rest[0] in RESULT_FILES) or (
            len(rest) >= 2 and rest[0] == "attempts" and path.suffix.casefold() == ".md"
        )

    def public(self, path: Path) -> bool:
        parts = self.relative_parts(path)
        if len(parts) == 1 and parts[0] in ROOT_DOCUMENTS:
            return True
        if parts and parts[0] in PUBLIC_DIRECTORIES:
            return True
        if parts[:2] == ("exercises", "01-documents"):
            rest = parts[2:]
            if rest[:1] == ("inputs",):
                return True
            if len(rest) == 1 and rest[0] in {
                "task.md",
                "readme.md",
                "inputs.sha256.json",
            }:
                return True
        return self.writable(path)

    def set_cwd(self, path: Path) -> None:
        if not path.is_dir() or not (
            path == self.root or path == self.root / EXERCISE or self.public(path)
        ):
            raise Denied(
                "Рабочая папка должна находиться в публичной области упражнения."
            )
        self.cwd = path

    def read(self, path: Path) -> None:
        if not self.public(path):
            raise Denied(
                "Читайте инструкции, task.md, inputs и публичные учебные материалы."
            )

    def write(self, path: Path) -> None:
        if not self.writable(path):
            raise Denied(
                "Менять можно только answer.md, my-prompt.md, notes.md и Markdown-файлы в attempts."
            )

    def scope(self, path: Path) -> None:
        self.read(path)
        if path.is_dir():
            for child in path.rglob("*"):
                resolved = self.path(str(child))
                self.read(resolved)


def file_argument(arguments: dict[str, object]) -> object:
    if (
        "file_path" in arguments
        and "path" in arguments
        and arguments["file_path"] != arguments["path"]
    ):
        raise Denied("Поля file_path и path должны однозначно указывать на один файл.")
    return arguments.get("file_path", arguments.get("path"))


def validate_glob_filter(pattern: object) -> str:
    if not isinstance(pattern, str) or not pattern or "\x00" in pattern:
        raise Denied("Нужен явный шаблон поиска в публичной папке.")
    normalized = pattern.replace("\\", "/")
    parts = PurePosixPath(normalized).parts
    if ".." in parts or any(part.casefold() in PRIVATE_PARTS for part in parts):
        raise Denied("Шаблон поиска не должен выходить из публичной области.")
    return normalized


def guard_glob(arguments: dict[str, object], policy: Policy) -> None:
    pattern = validate_glob_filter(arguments.get("pattern"))
    base = policy.path(arguments.get("path", str(policy.cwd)))
    static_parts = []
    for part in PurePosixPath(pattern).parts:
        if any(character in GLOB_CHARACTERS for character in part):
            break
        static_parts.append(part)
    target = policy.path(str(Path(*static_parts)) if static_parts else ".", base)
    try:
        policy.scope(target)
    except Denied as error:
        raise Denied(
            "Сузьте Glob до явной публичной папки, например inputs или docs; поиск по корню запрещён."
        ) from error


def guard_grep(arguments: dict[str, object], policy: Policy) -> None:
    if not isinstance(arguments.get("pattern"), str):
        raise Denied("Для Grep нужен строковый шаблон и явная публичная область.")
    path = policy.path(arguments.get("path", str(policy.cwd)))
    if "glob" in arguments:
        pattern = validate_glob_filter(arguments["glob"])
        if Path(pattern).is_absolute():
            raise Denied("Фильтр Grep должен быть относительным к области поиска.")
    try:
        policy.scope(path)
    except Denied as error:
        raise Denied(
            "Сузьте Grep до конкретного файла или публичной папки; поиск по корню запрещён."
        ) from error


def plain_arguments(arguments: list[str]) -> None:
    if any(
        any(character in GLOB_CHARACTERS for character in word) for word in arguments
    ):
        raise Denied("В командах указывайте конкретные пути, без шаблонов оболочки.")


def guard_checker(words: list[str], policy: Policy) -> None:
    arguments = words[1:]
    if words[0].casefold() in {"py", "py.exe"} and arguments[:1] == ["-3"]:
        arguments = arguments[1:]
    if len(arguments) != 3 or arguments[0] != "-I":
        raise Denied(
            "Разрешён только Python с -I, tools/check_answer.py и явным путём answer.md."
        )
    script = policy.path(arguments[1])
    expected = policy.root / "tools" / "check_answer.py"
    if script != expected or not script.is_file() or expected.resolve() != expected:
        raise Denied(
            "Разрешён только исходный tools/check_answer.py этого учебного репозитория."
        )
    answer = policy.path(arguments[2])
    if not policy.writable(answer) or answer.name.casefold() != "answer.md":
        raise Denied(
            "Проверке разрешено передать только answer.md из области результатов упражнения."
        )


def guard_shell(arguments: dict[str, object], policy: Policy) -> None:
    if any(
        arguments.get(key) is not None
        for key in ("shell", "env", "stdin", "input", "executable")
    ):
        raise Denied(
            "Переопределять оболочку, окружение или стандартный ввод в учебном профиле нельзя."
        )
    if (
        "command" in arguments
        and "cmd" in arguments
        and arguments["command"] != arguments["cmd"]
    ):
        raise Denied("Поля command и cmd должны содержать одну команду.")
    for key in ("workdir", "cwd"):
        if key in arguments:
            policy.set_cwd(policy.path(arguments[key]))
    command = arguments.get("command", arguments.get("cmd"))
    if (
        not isinstance(command, str)
        or not command
        or any(character in SHELL_META for character in command)
    ):
        raise Denied(
            "Разрешены только простые команды чтения без цепочек, подстановок и перенаправлений."
        )
    try:
        words = shlex.split(command.replace("\\", "/"))
    except ValueError as error:
        raise Denied("Не удалось разобрать простую команду оболочки.") from error
    if not words:
        raise Denied("Пустая команда не является учебной операцией.")
    name = words[0].casefold()
    plain_arguments(words)
    if name in {"python", "python3", "py", "python.exe", "python3.exe", "py.exe"}:
        guard_checker(words, policy)
        return
    if name == "pwd" and len(words) == 1:
        return
    if name in {"ls", "dir"}:
        listed_paths: list[Path] = []
        for word in words[1:]:
            if name == "ls" and word in {"-l", "-a", "-la", "-al"}:
                continue
            if word.startswith("-") or (name == "dir" and word.startswith("/")):
                raise Denied(
                    "Рекурсивный просмотр и дополнительные параметры ls/dir запрещены."
                )
            listed_paths.append(policy.path(word))
        for path in listed_paths or [policy.cwd]:
            if path != policy.root and path != policy.root / EXERCISE:
                policy.read(path)
        return
    if name in {"cat", "get-content"}:
        paths = words[1:]
        if name == "get-content" and paths[:1] in (["-LiteralPath"], ["-Path"]):
            paths = paths[1:]
        if not paths or any(path.startswith("-") for path in paths):
            raise Denied(
                "Для чтения укажите конкретные публичные файлы без дополнительных параметров."
            )
        for raw in paths:
            path = policy.path(raw)
            policy.read(path)
            if not path.is_file():
                raise Denied("Команда чтения требует явный существующий файл.")
        return
    if name == "rg" and len(words) == 3:
        if words[1] != "--files" and words[1].startswith("-"):
            raise Denied(
                "Параметры запуска дополнительных программ через rg запрещены."
            )
        scope = policy.path(words[2])
        if words[1] == "--files" and not scope.is_dir():
            raise Denied("Для rg --files укажите явную публичную папку.")
        policy.scope(scope)
        return
    raise Denied(
        "Этот профиль допускает только pwd, ls/dir, cat/Get-Content, ограниченный rg и изолированную проверку ответа."
    )


def guard_patch(arguments: dict[str, object], policy: Policy) -> None:
    command = arguments.get("command")
    if not isinstance(command, str):
        raise Denied("Для apply_patch нужен текст патча в command.")
    lines = command.strip().splitlines()
    if not lines or lines[0] != "*** Begin Patch" or lines[-1] != "*** End Patch":
        raise Denied("Не удалось определить границы патча.")
    operation = None
    operations = 0
    for line in lines[1:-1]:
        header = re.fullmatch(r"\*\*\* (Add|Update|Delete) File: (.+)", line)
        if header:
            operation = header.group(1)
            operations += 1
            policy.write(policy.path(header.group(2)))
            continue
        move = re.fullmatch(r"\*\*\* Move to: (.+)", line)
        if move:
            if operation != "Update":
                raise Denied(
                    "Перемещение допускается только для явно обновляемого файла результата."
                )
            policy.write(policy.path(move.group(1)))
            continue
        if line.startswith("*** ") and line != "*** End of File":
            raise Denied("Патч содержит неизвестный или неполный заголовок операции.")
    if not operations:
        raise Denied("Патч не содержит явных операций над файлами результата.")


def decision(event: object, root: Path) -> dict[str, object]:
    """Return an empty object for permitted operations, otherwise a shared deny object."""
    try:
        if not isinstance(event, dict) or event.get("hook_event_name") != "PreToolUse":
            raise Denied("Ожидается JSON-событие PreToolUse.")
        tool = event.get("tool_name")
        arguments = event.get("tool_input")
        if not isinstance(tool, str) or not isinstance(arguments, dict):
            raise Denied("Нужны строковое tool_name и объект tool_input.")
        if tool in METADATA_TOOLS:
            return {}
        if tool == "write_stdin":
            if arguments.get("chars", "") == "":
                return {}
            raise Denied("Передача команд в уже запущенный процесс запрещена.")
        policy = Policy(root, event.get("cwd"))
        if tool == "Read":
            policy.read(policy.path(file_argument(arguments)))
        elif tool in {"Write", "Edit"}:
            policy.write(policy.path(file_argument(arguments)))
        elif tool == "Glob":
            guard_glob(arguments, policy)
        elif tool == "Grep":
            guard_grep(arguments, policy)
        elif tool == "Bash":
            guard_shell(arguments, policy)
        elif tool == "apply_patch":
            guard_patch(arguments, policy)
        else:
            raise Denied("Инструмент не входит в разрешённый набор первого упражнения.")
        return {}
    except (Denied, OSError, RuntimeError, TypeError, ValueError) as error:
        return deny(str(error))


def main() -> int:
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    if isinstance(sys.stdin, io.TextIOWrapper):
        sys.stdin.reconfigure(encoding="utf-8-sig")
    try:
        event = json.load(sys.stdin)
        output = decision(event, Path(__file__).resolve().parents[1])
    except (json.JSONDecodeError, UnicodeError, OSError, RecursionError, ValueError):
        output = deny(
            "Не удалось прочитать JSON-событие PreToolUse. Действие запрещено."
        )
    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
