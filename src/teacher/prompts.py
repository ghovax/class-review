"""Strict rendering for the packaged prompt templates."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from importlib import resources

from teacher.support import OperationError

_PLACEHOLDER = re.compile(r"\{\{\s+([A-Za-z0-9_.-]+)\s+\}\}")


class Prompts:
    """Reads packaged prompts and rejects missing or unused values."""

    def __init__(self, package: str = "teacher") -> None:
        self.package = package

    def render(self, name: str, variables: Mapping[str, object] | None = None) -> str:
        if name.startswith("/") or ".." in name.split("/"):
            raise OperationError.terminal("invalid prompt name", {"name": name})
        try:
            template = resources.files(self.package).joinpath(f"{name}.md").read_text()
        except (FileNotFoundError, ModuleNotFoundError, OSError) as error:
            raise OperationError.terminal(
                "prompt could not be read", {"name": name}, cause=error
            ) from error
        supplied = variables or {}
        names = set(_PLACEHOLDER.findall(template))
        missing = sorted(item for item in names if _value(supplied, item) is None)
        unused = sorted(
            item
            for item in _leaf_names(supplied)
            if not any(item == used or item.startswith(f"{used}.") for used in names)
        )
        if missing or unused:
            raise OperationError.terminal(
                "prompt values do not match its placeholders",
                {"name": name, "missing": missing, "unused": unused},
            )
        return _PLACEHOLDER.sub(lambda match: _render(_value(supplied, match.group(1))), template)


def _value(values: Mapping[str, object], dotted_name: str) -> object | None:
    current: object = values
    for part in dotted_name.split("."):
        current = (
            current.get(part) if isinstance(current, Mapping) else getattr(current, part, None)
        )
        if current is None:
            return None
    return current


def _leaf_names(values: Mapping[str, object], prefix: str = "") -> set[str]:
    names: set[str] = set()
    for key, value in values.items():
        name = f"{prefix}.{key}" if prefix else str(key)
        names.update(_leaf_names(value, name) if isinstance(value, Mapping) else {name})
    return names


def _render(value: object | None) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)
