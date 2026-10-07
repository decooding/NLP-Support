"""Проверка каркаса пакета: все подпакеты существуют, импортируются и документированы."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"

EXPECTED_PACKAGES = [
    "support_dispatcher",
    "support_dispatcher.api",
    "support_dispatcher.api.routes",
    "support_dispatcher.core",
    "support_dispatcher.domain",
    "support_dispatcher.preprocessing",
    "support_dispatcher.system1",
    "support_dispatcher.system2",
    "support_dispatcher.system2.prompts",
    "support_dispatcher.resilience",
    "support_dispatcher.pipeline",
    "support_dispatcher.routing",
    "support_dispatcher.review",
    "support_dispatcher.observability",
    "support_dispatcher.infrastructure",
    "support_dispatcher.evaluation",
]


@pytest.mark.parametrize("name", EXPECTED_PACKAGES)
def test_package_importable_and_documented(name: str) -> None:
    module = importlib.import_module(name)
    assert module.__doc__ and module.__doc__.strip(), f"{name} has no docstring"


def test_py_typed_marker_present() -> None:
    assert (SRC / "support_dispatcher" / "py.typed").is_file()


def test_no_unexpected_packages() -> None:
    found = {
        ".".join(p.parent.relative_to(SRC).parts)
        for p in (SRC / "support_dispatcher").rglob("__init__.py")
    }
    assert found == set(EXPECTED_PACKAGES)
