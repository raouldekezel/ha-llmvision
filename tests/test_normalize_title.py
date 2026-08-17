"""Tests for ``normalize_title`` — the structural title sanitizer.

Black-box per the fork's test policy: the parametrized table drives the public
module function ``normalize_title`` directly; the provider-path wiring is pinned
separately in ``test_providers.py`` (an apostrophe-bearing title survives
``Request.call``). No implementation detail is read.

Rules exercised: NFC; fixed-point unwrapping of quotes/emphasis and a leading
``Title:`` label; first-sentence extraction (newline and full-width terminators
unconditional, ASCII ``"<.!?> "`` boundaries guarded by a 12-char minimum cut);
whitespace collapse; one trailing period dropped. No character filtering of any
kind — every script and both apostrophes (U+0027, U+2019) survive.
"""

import pytest

from custom_components.llmvision.providers import normalize_title


CASES = [
    # Apostrophes survive — the whole point of BUG-01.
    ("Homme vu à l'allée", "Homme vu à l'allée"),  # U+0027
    ("L’homme s’approche", "L’homme s’approche"),  # U+2019
    # Wrapping pairs peeled.
    ('"Person at door."', "Person at door"),
    ("“Personne à la porte.”", "Personne à la porte"),
    ("« Chat sur le muret »", "Chat sur le muret"),
    ("**Bold title**", "Bold title"),
    # Leading label, incl. the fixed-point interaction with newline / wrapping (R1).
    ("Title:\nPerson at door", "Person at door"),
    ('Title: "Person at door"', "Person at door"),
    ("Titre : Chien au portail.", "Chien au portail"),
    ("Título: Perro en el jardín", "Perro en el jardín"),
    # First-sentence extraction.
    ("Person at door. He carries a box.", "Person at door"),
    ("¡Perro en el jardín! Ladra sin parar.", "¡Perro en el jardín!"),
    # Minimum-cut guard against abbreviations (R2).
    ("M. Dupont à la porte", "M. Dupont à la porte"),
    ("Mr. Smith at the door. Waves.", "Mr. Smith at the door"),
    # Newline is exempt from the guard.
    ("Chien\nLe chien aboie", "Chien"),
    # Full-width terminators (R3), no minimum-cut.
    ("人が玄関にいます。荷物を持っています。", "人が玄関にいます"),
    # Sentinel used by the "no activity" filter stays matchable.
    ("No activity observed.", "No activity observed"),
    ("No activity observed. The scene is empty.", "No activity observed"),
    # Trailing ellipsis kept; no character filtering.
    ("Attention…", "Attention…"),
    ("Собака 🐕 у ворот", "Собака 🐕 у ворот"),
    # Decorations-only reduces to empty (the caller's fallback owns empties).
    ('""', ""),
    ("**", ""),
]


@pytest.mark.parametrize("raw,expected", CASES)
def test_normalize_title(raw, expected):
    assert normalize_title(raw) == expected


@pytest.mark.parametrize("raw,expected", CASES)
def test_normalize_title_idempotent(raw, expected):
    once = normalize_title(raw)
    assert normalize_title(once) == once


def test_normalize_title_does_no_character_filtering():
    # Angle brackets and ampersands are kept verbatim — making rendered data
    # inert is the card's job (render boundary), not the stored title's.
    assert normalize_title("A <b> tag & more") == "A <b> tag & more"


def test_normalize_title_empty_input():
    assert normalize_title("") == ""
    assert normalize_title("   \n\t  ") == ""
