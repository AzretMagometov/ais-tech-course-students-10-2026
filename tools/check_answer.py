"""Validate an exercise answer without judging its factual conclusion."""

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import sys


REQUIRED = ("Ответ", "Точная цитата", "Источник", "Проверка и ограничения")
EXERCISE = Path("exercises") / "01-documents"
MANUAL_LIMIT = "Вывод, число, единицы и условия сверьте с источником вручную."


class CheckError(ValueError):
    """A readable validation failure, safe to show to a learner."""


def read_text(path: Path) -> str:
    """Read UTF-8 documents and convert filesystem failures into diagnostics."""
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as error:
        raise CheckError(f"Не удалось прочитать {path.name}: {error}") from error


def parse_sections(text: str) -> dict[str, str]:
    """Collect level-two sections while ignoring headings inside code fences."""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    fence: str | None = None
    for line in text.splitlines():
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        if fence is not None:
            continue
        heading = re.match(r"^##[ \t]+(.+?)[ \t]*$", line)
        if heading:
            current = heading.group(1).strip()
            if current in sections:
                raise CheckError(f"Заголовок повторяется: {current}")
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return {title: "\n".join(lines).strip() for title, lines in sections.items()}


def check_inputs(exercise: Path) -> Path:
    """Check the manifest, exact input file list and hashes before trusting a source."""
    inputs = exercise / "inputs"
    if not inputs.is_dir() or inputs.is_symlink():
        raise CheckError("Папка inputs отсутствует или является символической ссылкой.")
    try:
        manifest = json.loads(read_text(exercise / "inputs.sha256.json"))
    except json.JSONDecodeError as error:
        raise CheckError(
            "Файл inputs.sha256.json содержит некорректный JSON."
        ) from error
    if not isinstance(manifest, dict) or not manifest:
        raise CheckError(
            "В inputs.sha256.json нужен непустой объект: имя файла и SHA-256."
        )
    for name, digest in manifest.items():
        if (
            not isinstance(name, str)
            or not name
            or name in (".", "..")
            or "/" in name
            or "\\" in name
            or not isinstance(digest, str)
            or not re.fullmatch(r"[0-9a-fA-F]{64}", digest)
        ):
            raise CheckError("Некорректное имя файла или SHA-256 в inputs.sha256.json.")
    actual: set[str] = set()
    for path in inputs.rglob("*"):
        if path.is_symlink():
            raise CheckError(f"В inputs найдена символическая ссылка: {path.name}")
        if path.is_file():
            actual.add(path.relative_to(inputs).as_posix())
    if actual != set(manifest):
        raise CheckError(
            "Изменён список исходных файлов inputs. Восстановите исходники упражнения."
        )
    for name, digest in manifest.items():
        path = inputs / name
        try:
            actual_digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as error:
            raise CheckError(
                f"Не удалось прочитать исходник {name}: {error}"
            ) from error
        if actual_digest != digest.lower():
            raise CheckError(f"Исходник изменён: {name}. Восстановите исходный файл.")
    return inputs.resolve()


def source_fields(section: str) -> tuple[str, str]:
    """Read the two explicit source fields without interpreting arbitrary Markdown."""
    values: dict[str, str] = {}
    for label in ("Файл", "Раздел"):
        matches = re.findall(r"^" + label + r":[ \t]*(.+)$", section, re.M)
        if len(matches) != 1:
            raise CheckError(
                f"В разделе Источник нужна одна строка «{label}: значение»."
            )
        values[label] = matches[0].strip().strip("`")
        if not values[label]:
            raise CheckError(f"Не заполнено поле {label}.")
    return values["Файл"], values["Раздел"]


def source_section(document: str, title: str) -> str:
    """Locate one heading and return its body, stopping at a peer or parent heading."""
    lines = document.splitlines()
    headings = []
    for index, line in enumerate(lines):
        match = re.match(r"^(#{1,6})[ \t]+(.+?)[ \t]*$", line)
        if match:
            headings.append((index, len(match.group(1)), match.group(2).strip()))
    selected = [heading for heading in headings if heading[2] == title]
    if len(selected) != 1:
        raise CheckError(f"Указанный раздел не найден однозначно: {title}")
    start, level, _ = selected[0]
    end = next(
        (index for index, depth, _ in headings if index > start and depth <= level),
        len(lines),
    )
    return "\n".join(lines[start + 1 : end]).strip()


def quoted_blocks(section: str) -> list[str]:
    """Return exact blockquote text, preserving paragraph boundaries."""
    blocks: list[str] = []
    current: list[str] = []
    for line in section.splitlines():
        match = re.match(r"^>[ ]?(.*)$", line)
        if match:
            current.append(match.group(1))
        elif current:
            blocks.append("\n".join(current).strip())
            current = []
    if current:
        blocks.append("\n".join(current).strip())
    blocks = [block for block in blocks if block]
    if not blocks:
        raise CheckError(
            "В разделе Точная цитата нужна непустая цитата строками с символом >."
        )
    return blocks


def check_answer(answer: Path) -> list[str]:
    """Return validation problems; successful checks do not verify the conclusion."""
    try:
        answer = answer.resolve()
        exercise = answer.parent
        inputs = check_inputs(exercise)
        sections = parse_sections(read_text(answer))
        for title in REQUIRED:
            if not sections.get(title):
                raise CheckError(f"Нет непустого раздела: {title}")
        filename, title = source_fields(sections["Источник"])
        relative = PurePosixPath(filename.replace("\\", "/"))
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or relative.parts[:1] != ("inputs",)
        ):
            raise CheckError(
                "Поле Файл должно указывать на файл внутри inputs, например inputs/manual.md."
            )
        source = (exercise / Path(*relative.parts)).resolve()
        if not source.is_relative_to(inputs) or not source.is_file():
            raise CheckError(
                "Файл источника отсутствует или находится за пределами inputs."
            )
        body = source_section(read_text(source), title)
        for quote in quoted_blocks(sections["Точная цитата"]):
            if quote not in body:
                raise CheckError(
                    "Цитата не совпадает дословно с текстом указанного раздела источника."
                )
        return []
    except (CheckError, OSError, ValueError) as error:
        return [str(error)]


def find_exercise_root(cwd: object) -> Path:
    """Search only the current folder and its parents for this exercise manifest."""
    if not isinstance(cwd, str) or not cwd or not Path(cwd).is_absolute():
        raise CheckError("Событие Stop должно содержать абсолютный путь cwd.")
    folder = Path(cwd).resolve()
    if not folder.is_dir():
        raise CheckError("Рабочая папка cwd отсутствует.")
    for candidate in (folder, *folder.parents):
        if (candidate / EXERCISE / "inputs.sha256.json").is_file():
            return candidate
    raise CheckError(
        "В cwd и родительских папках не найдено первое учебное упражнение."
    )


def run_hook() -> int:
    """Return a Stop decision, allowing at most one automatic correction cycle."""
    event = None
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            raise CheckError("Событие Stop должно быть JSON-объектом.")
        if event.get("hook_event_name", "Stop") != "Stop":
            raise CheckError("Этот обработчик поддерживает только событие Stop.")
        root = find_exercise_root(event.get("cwd"))
        problems = check_answer(root / EXERCISE / "answer.md")
    except (
        json.JSONDecodeError,
        UnicodeError,
        CheckError,
        OSError,
        ValueError,
    ) as error:
        problems = [f"Не удалось проверить результат: {error}"]
    output: dict[str, str] = {}
    if problems:
        reason = "; ".join(problems)
        if isinstance(event, dict) and event.get("stop_hook_active") is True:
            output = {
                "systemMessage": "Повторная проверка не пройдена: "
                + reason
                + ". Проверьте результат вручную."
            }
        else:
            output = {
                "decision": "block",
                "reason": reason + ". Исправьте результат упражнения. " + MANUAL_LIMIT,
            }
    print(json.dumps(output, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Проверить структуру ответа, исходники и дословность цитаты."
    )
    parser.add_argument(
        "answer",
        nargs="?",
        default=str(EXERCISE / "answer.md"),
        help="путь к Markdown-ответу",
    )
    parser.add_argument(
        "--hook",
        action="store_true",
        help="обработать событие Stop из стандартного ввода",
    )
    options = parser.parse_args()
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    if options.hook:
        if isinstance(sys.stdin, io.TextIOWrapper):
            sys.stdin.reconfigure(encoding="utf-8-sig")
        return run_hook()
    problems = check_answer(Path(options.answer))
    if problems:
        for problem in problems:
            print("Ошибка: " + problem)
        return 1
    print("Проверены структура ответа, исходники, раздел и дословность цитаты.")
    print(MANUAL_LIMIT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
