from __future__ import annotations

import json

from src.services.publications.lineage import compute_config_hash, derive_size_from_visual_config


def test_config_hash_deterministic() -> None:
    assert compute_config_hash('bar', (1080, 1080), 'Inflation') == compute_config_hash('bar', (1080, 1080), 'Inflation')


def test_config_hash_changes_for_inputs() -> None:
    base = compute_config_hash('bar', (1080, 1080), 'X')
    assert base != compute_config_hash('line', (1080, 1080), 'X')
    assert base != compute_config_hash('bar', (1200, 900), 'X')
    assert base != compute_config_hash('bar', (1080, 1080), 'Copy of X')


def test_config_hash_64_hex() -> None:
    h = compute_config_hash('bar', (1080, 1080), 'X')
    assert len(h) == 64
    assert all(c in '0123456789abcdef' for c in h)


def test_derive_size_defaults() -> None:
    assert derive_size_from_visual_config(None) == (1080, 1080)
    assert derive_size_from_visual_config('') == (1080, 1080)
    assert derive_size_from_visual_config('{not json') == (1080, 1080)


def test_derive_size_root_preset_shape() -> None:
    cfg = json.dumps({'size': 'twitter'})
    assert derive_size_from_visual_config(cfg) == (1200, 675)


def test_derive_size_nested_and_explicit_dict() -> None:
    cfg_nested = json.dumps({'page': {'size': 'instagram_port'}})
    cfg_dict = json.dumps({'page': {'size': {'w': 800, 'h': 600}}})
    assert derive_size_from_visual_config(cfg_nested) == (1080, 1350)
    assert derive_size_from_visual_config(cfg_dict) == (800, 600)
