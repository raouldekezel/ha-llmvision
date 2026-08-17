"""Tests for ``normalize_title`` — the structural title sanitizer.

Black-box per the fork's test policy: the parametrized table drives the public
module function ``normalize_title`` directly; the provider-path wiring is pinned
separately in ``test_providers.py`` (an apostrophe-bearing title survives
``Request.call``). No implementation detail is read.

Rules exercised: NFC; fixed-point unwrapping of quotes/emphasis and a leading
label (``Title:`` … ``标题：``); first-sentence extraction (newline unconditional;
full-width/danda ``。！？।`` guarded by a 4-char minimum cut; ASCII/Arabic
``"<.!?؟> "`` boundaries guarded by a 12-char minimum cut plus a short-token
guard for ``.`` and a not-lowercase/not-digit follower guard); whitespace
collapse; one trailing ``.``/``。``/``।`` dropped. No character filtering of any
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
    # --- i18n boundary hardening (BUG-01 multilingual audit) ----------------
    # (a) short-token guard: an abbreviation past index 12 must not truncate.
    ("Colis déposé chez M. Dupont. Personne ne sort.", "Colis déposé chez M. Dupont"),
    ("Delivery for Mr. and Mrs. Smith. No answer.", "Delivery for Mr. and Mrs. Smith"),
    ("Pacco per il Sig. Rossi al cancello. Attende.", "Pacco per il Sig. Rossi al cancello"),
    ("Paketet står vid fam. Larssons grind. Ingen öppnar.", "Paketet står vid fam. Larssons grind"),
    ("Șoferul așteaptă la poartă. Nu coboară.", "Șoferul așteaptă la poartă"),
    ("وصل طرد للسيد م. أحمد عند الباب. لا أحد يفتح.", "وصل طرد للسيد م. أحمد عند الباب"),
    # (b') follower guard: a digit or lowercase after the space must not cut.
    ("Lieferwagen hält in der Bahnhofstr. 12 am Tor", "Lieferwagen hält in der Bahnhofstr. 12 am Tor"),
    ("Balík u dveří č. 5 zůstává ležet", "Balík u dveří č. 5 zůstává ležet"),
    ("Csomag várakozik a 3. emeleten a kapunál", "Csomag várakozik a 3. emeleten a kapunál"),
    ("Paczka przy ul. Głównej. Nikt nie wychodzi.", "Paczka przy ul. Głównej"),
    ("Encomenda para o Sr. Silva no 3.º andar. Ninguém abre.", "Encomenda para o Sr. Silva no 3.º andar"),
    # Expressive marks kept; inverted / Greek punctuation handled gracefully.
    ("¿Quién anda ahí? El perro ladra.", "¿Quién anda ahí?"),
    ("Ποιος είναι εκεί; Ο σκύλος γαβγίζει.", "Ποιος είναι εκεί; Ο σκύλος γαβγίζει"),
    # Leading U+2019 elision must not be peeled (no matching opener).
    ("’s Avonds staat iemand bij ’t hek", "’s Avonds staat iemand bij ’t hek"),
    # Mid-dot (ex-whitelist casualty) and German low-quote wrapping.
    ("Paral·lelament, un home espera al portal", "Paral·lelament, un home espera al portal"),
    ("„Bewegung im Garten“", "Bewegung im Garten"),
    # Caseless scripts still cut on ASCII "." (b' passes: not lowercase/digit).
    ("문 앞에 사람이 서 있습니다. 개가 짖고 있습니다.", "문 앞에 사람이 서 있습니다"),
    # Full-width / danda cut guarded by MIN_CUT_CJK = 4.
    ("雨。傘を持った人が門の前にいる", "雨。傘を持った人が門の前にいる"),
    ("门口有一个人。狗叫了。", "门口有一个人"),
    ("注意！有人翻墙进入院子", "注意！有人翻墙进入院子"),
    ("दरवाज़े पर आदमी खड़ा है। कुत्ता भौंक रहा है।", "दरवाज़े पर आदमी खड़ा है"),
    # Arabic ؟ kept (like "?"), no cut below the Latin MIN_CUT.
    ("من بالباب؟ الكلب ينبح.", "من بالباب؟ الكلب ينبح"),
    # CJK title label + full-width colon, and CJK title brackets.
    ("标题：门口的人", "门口的人"),
    ("《门口的人》", "门口的人"),
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
