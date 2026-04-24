"""Tests for scripts/arb_parity.py using synthetic fixtures."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "arb_parity.py"


def run_script(en_path, ru_path, *extra):
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--en",
            str(en_path),
            "--ru",
            str(ru_path),
            *extra,
        ],
        capture_output=True,
        text=True,
    )


def write_arb(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def tmp_arbs(tmp_path):
    en = tmp_path / "en.arb"
    ru = tmp_path / "ru.arb"
    return en, ru


def test_clean_parity_exits_zero(tmp_arbs):
    en, ru = tmp_arbs
    write_arb(
        en,
        {
            "@@locale": "en",
            "hello": "Hello",
            "@hello": {"description": "Greeting"},
        },
    )
    write_arb(ru, {"@@locale": "ru", "hello": "Привет"})
    result = run_script(en, ru)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout


def test_missing_ru_key_exits_one(tmp_arbs):
    en, ru = tmp_arbs
    write_arb(en, {"@@locale": "en", "hello": "Hello", "extra": "Extra"})
    write_arb(ru, {"@@locale": "ru", "hello": "Привет"})
    result = run_script(en, ru)
    assert result.returncode == 1
    assert "DRIFT" in result.stdout
    assert "extra" in result.stdout.lower()


def test_missing_en_key_exits_one(tmp_arbs):
    en, ru = tmp_arbs
    write_arb(en, {"@@locale": "en", "hello": "Hello"})
    write_arb(ru, {"@@locale": "ru", "hello": "Привет", "extra": "Экстра"})
    result = run_script(en, ru)
    assert result.returncode == 1


def test_placeholder_mismatch_exits_one(tmp_arbs):
    en, ru = tmp_arbs
    write_arb(
        en,
        {
            "@@locale": "en",
            "greeting": "Hello {name}",
            "@greeting": {"placeholders": {"name": {"type": "String"}}},
        },
    )
    write_arb(ru, {"@@locale": "ru", "greeting": "Привет"})
    result = run_script(en, ru)
    assert result.returncode == 1
    assert "placeholder" in result.stdout.lower()


def test_metadata_declaration_mismatch_exits_one(tmp_arbs):
    en, ru = tmp_arbs
    write_arb(
        en,
        {
            "@@locale": "en",
            "greeting": "Hello {name}",
            "@greeting": {"placeholders": {"name": {}, "unused": {}}},
        },
    )
    write_arb(ru, {"@@locale": "ru", "greeting": "Привет {name}"})
    result = run_script(en, ru)
    assert result.returncode == 1


def test_json_output_parseable(tmp_arbs):
    en, ru = tmp_arbs
    write_arb(en, {"@@locale": "en", "hello": "Hello"})
    write_arb(ru, {"@@locale": "ru", "hello": "Привет"})
    result = run_script(en, ru, "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["status"] == "clean"
    assert data["en_count"] == 1


def test_missing_arb_file_exits_two(tmp_arbs):
    en, ru = tmp_arbs
    write_arb(en, {"@@locale": "en", "hello": "Hello"})
    # ru file never created
    result = run_script(en, ru)
    assert result.returncode == 2


def test_invalid_json_exits_two(tmp_arbs):
    en, ru = tmp_arbs
    en.write_text("{ invalid json ", encoding="utf-8")
    write_arb(ru, {"@@locale": "ru", "hello": "Привет"})
    result = run_script(en, ru)
    assert result.returncode == 2


def test_strict_metadata_flags_ru_metadata(tmp_arbs):
    en, ru = tmp_arbs
    write_arb(en, {"@@locale": "en", "hello": "Hello"})
    write_arb(
        ru,
        {
            "@@locale": "ru",
            "hello": "Привет",
            "@hello": {"description": "should not be here"},
        },
    )
    # Without --strict-metadata: exit 0 (RU metadata ignored for parity)
    result = run_script(en, ru)
    assert result.returncode == 0
    # With --strict-metadata: exit 1
    result_strict = run_script(en, ru, "--strict-metadata")
    assert result_strict.returncode == 1
