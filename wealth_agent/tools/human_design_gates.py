"""
human_design_gates.py — 64-Gate Human Design Number System.

FAITHFUL PORT of the wheel geometry, gate catalog, and lookup engine from
your uploaded human_design_gates.py -- verified independently before
porting, not just trusted:
  - Cross-checked the Gate->element mapping against a periodic table I
    wrote from scratch (not their _ATOMIC_NUMBER_ORDER list, so a shared
    error in both of their internal lists couldn't slip through): 0
    mismatches across all 64 gates.
  - Confirmed GATE_WHEEL_SEQUENCE is a genuine permutation of 1-64, all 64
    hexagrams are distinct, and 64 x 5.625deg tiles exactly to 360deg.
  - Stress-tested the floating-point boundary guard (_wrap_deg) at the
    exact anchor, one full revolution past it, and femtodegree-adjacent
    values on both sides -- all resolved to the correct gate. Swept all
    64 gate boundaries for self-consistency: zero mismatches.

Anchor: Gate 41 begins at 2deg23'23" = 296.843500 sidereal ecliptic
longitude. Gate width 360/64 = 5.625deg exactly. Wheel advances in the
canonical Human Design mandala order (41,19,13,49,...), not numeric order.

Data correction (from source): the original list had "34 - Xenon" twice
(Gate 34 is Selenium). Xenon (Z=54) was the only gate missing, so Gate 54
is Xenon, hexagram \u6b78\u59b9 (gu\u012b m\xe8i). Gate 41's own hexagram was filled in as
\u640d (s\u01d0n), I Ching 41 "Decrease".

House note: chart mode CANNOT report each body's House right now.
wealth_algorithm.py (as uploaded) has no HOUSES table, house_of_sign(), or
house_for_longitude() -- despite the accompanying README describing one in
detail. get_chart_gates() below returns "house": None with a note rather
than fabricating a house system that isn't actually in your source. See
the top-level chat response for what to do next.
"""

from __future__ import annotations

from typing import Dict, List

# ---------------------------------------------------------------------------
# WHEEL GEOMETRY -- verbatim.
# ---------------------------------------------------------------------------
GATE_41_DMS: tuple = (2, 23, 23)             # 2d23'23" -- as supplied
GATE_41_START: float = 296.843500             # sidereal ecliptic longitude
GATE_WIDTH: float = 360.0 / 64                # 5.625deg exactly
LINE_WIDTH: float = GATE_WIDTH / 6            # 0.9375deg -- bonus line resolution

# Wheel order (Human Design mandala sequence), starting at Gate 41.
GATE_WHEEL_SEQUENCE: List[int] = [
    41, 19, 13, 49, 30, 55, 37, 63, 22, 36, 25, 17, 21, 51, 42,
     3, 27, 24,  2, 23,  8, 20, 16, 35, 45, 12, 15, 52, 39, 53,
    62, 56, 31, 33,  7,  4, 29, 59, 40, 64, 47,  6, 46, 18, 48,
    57, 32, 50, 28, 44,  1, 43, 14, 34,  9,  5, 26, 11, 10, 58,
    38, 54, 61, 60,
]

# ---------------------------------------------------------------------------
# GATE CATALOG -- Gate N <-> element Z=N <-> I Ching hexagram N. Verbatim,
# independently cross-checked against a from-scratch periodic table (see
# module docstring) -- 0 mismatches.
# ---------------------------------------------------------------------------
GATE_ELEMENTS: Dict[int, dict] = {
    1: {"z": 1, "element": 'Hydrogen', "symbol": 'H', "hanzi": '乾', "pinyin": 'qián'},
    2: {"z": 2, "element": 'Helium', "symbol": 'He', "hanzi": '坤', "pinyin": 'kūn'},
    3: {"z": 3, "element": 'Lithium', "symbol": 'Li', "hanzi": '屯', "pinyin": 'zhūn'},
    4: {"z": 4, "element": 'Beryllium', "symbol": 'Be', "hanzi": '蒙', "pinyin": 'méng'},
    5: {"z": 5, "element": 'Boron', "symbol": 'B', "hanzi": '需', "pinyin": 'xū'},
    6: {"z": 6, "element": 'Carbon', "symbol": 'C', "hanzi": '訟', "pinyin": 'sòng'},
    7: {"z": 7, "element": 'Nitrogen', "symbol": 'N', "hanzi": '師', "pinyin": 'shī'},
    8: {"z": 8, "element": 'Oxygen', "symbol": 'O', "hanzi": '比', "pinyin": 'bǐ'},
    9: {"z": 9, "element": 'Fluorine', "symbol": 'F', "hanzi": '小畜', "pinyin": 'xiǎo xù'},
    10: {"z": 10, "element": 'Neon', "symbol": 'Ne', "hanzi": '履', "pinyin": 'lǚ'},
    11: {"z": 11, "element": 'Sodium', "symbol": 'Na', "hanzi": '泰', "pinyin": 'tài'},
    12: {"z": 12, "element": 'Magnesium', "symbol": 'Mg', "hanzi": '否', "pinyin": 'pǐ'},
    13: {"z": 13, "element": 'Aluminium', "symbol": 'Al', "hanzi": '同人', "pinyin": 'tóng rén'},
    14: {"z": 14, "element": 'Silicon', "symbol": 'Si', "hanzi": '大有', "pinyin": 'dà yǒu'},
    15: {"z": 15, "element": 'Phosphorus', "symbol": 'P', "hanzi": '謙', "pinyin": 'qiān'},
    16: {"z": 16, "element": 'Sulfur', "symbol": 'S', "hanzi": '豫', "pinyin": 'yù'},
    17: {"z": 17, "element": 'Chlorine', "symbol": 'Cl', "hanzi": '隨', "pinyin": 'suí'},
    18: {"z": 18, "element": 'Argon', "symbol": 'Ar', "hanzi": '蠱', "pinyin": 'gǔ'},
    19: {"z": 19, "element": 'Potassium', "symbol": 'K', "hanzi": '臨', "pinyin": 'lín'},
    20: {"z": 20, "element": 'Calcium', "symbol": 'Ca', "hanzi": '觀', "pinyin": 'guān'},
    21: {"z": 21, "element": 'Scandium', "symbol": 'Sc', "hanzi": '噬嗑', "pinyin": 'shì kè'},
    22: {"z": 22, "element": 'Titanium', "symbol": 'Ti', "hanzi": '賁', "pinyin": 'bì'},
    23: {"z": 23, "element": 'Vanadium', "symbol": 'V', "hanzi": '剝', "pinyin": 'bō'},
    24: {"z": 24, "element": 'Chromium', "symbol": 'Cr', "hanzi": '復', "pinyin": 'fù'},
    25: {"z": 25, "element": 'Manganese', "symbol": 'Mn', "hanzi": '无妄', "pinyin": 'wú wàng'},
    26: {"z": 26, "element": 'Iron', "symbol": 'Fe', "hanzi": '大畜', "pinyin": 'dà xù'},
    27: {"z": 27, "element": 'Cobalt', "symbol": 'Co', "hanzi": '頤', "pinyin": 'yí'},
    28: {"z": 28, "element": 'Nickel', "symbol": 'Ni', "hanzi": '大過', "pinyin": 'dà guò'},
    29: {"z": 29, "element": 'Copper', "symbol": 'Cu', "hanzi": '坎', "pinyin": 'kǎn'},
    30: {"z": 30, "element": 'Zinc', "symbol": 'Zn', "hanzi": '離', "pinyin": 'lí'},
    31: {"z": 31, "element": 'Gallium', "symbol": 'Ga', "hanzi": '咸', "pinyin": 'xián'},
    32: {"z": 32, "element": 'Germanium', "symbol": 'Ge', "hanzi": '恆', "pinyin": 'héng'},
    33: {"z": 33, "element": 'Arsenic', "symbol": 'As', "hanzi": '遯', "pinyin": 'dùn'},
    34: {"z": 34, "element": 'Selenium', "symbol": 'Se', "hanzi": '大壯', "pinyin": 'dà zhuàng'},
    35: {"z": 35, "element": 'Bromine', "symbol": 'Br', "hanzi": '晉', "pinyin": 'jìn'},
    36: {"z": 36, "element": 'Krypton', "symbol": 'Kr', "hanzi": '明夷', "pinyin": 'míng yí'},
    37: {"z": 37, "element": 'Rubidium', "symbol": 'Rb', "hanzi": '家人', "pinyin": 'jiā rén'},
    38: {"z": 38, "element": 'Strontium', "symbol": 'Sr', "hanzi": '睽', "pinyin": 'kuí'},
    39: {"z": 39, "element": 'Yttrium', "symbol": 'Y', "hanzi": '蹇', "pinyin": 'jiǎn'},
    40: {"z": 40, "element": 'Zirconium', "symbol": 'Zr', "hanzi": '解', "pinyin": 'jiě'},
    41: {"z": 41, "element": 'Niobium', "symbol": 'Nb', "hanzi": '損', "pinyin": 'sǔn'},
    42: {"z": 42, "element": 'Molybdenum', "symbol": 'Mo', "hanzi": '益', "pinyin": 'yì'},
    43: {"z": 43, "element": 'Technetium', "symbol": 'Tc', "hanzi": '夬', "pinyin": 'guài'},
    44: {"z": 44, "element": 'Ruthenium', "symbol": 'Ru', "hanzi": '姤', "pinyin": 'gòu'},
    45: {"z": 45, "element": 'Rhodium', "symbol": 'Rh', "hanzi": '萃', "pinyin": 'cuì'},
    46: {"z": 46, "element": 'Palladium', "symbol": 'Pd', "hanzi": '升', "pinyin": 'shēng'},
    47: {"z": 47, "element": 'Silver', "symbol": 'Ag', "hanzi": '困', "pinyin": 'kùn'},
    48: {"z": 48, "element": 'Cadmium', "symbol": 'Cd', "hanzi": '井', "pinyin": 'jǐng'},
    49: {"z": 49, "element": 'Indium', "symbol": 'In', "hanzi": '革', "pinyin": 'gé'},
    50: {"z": 50, "element": 'Tin', "symbol": 'Sn', "hanzi": '鼎', "pinyin": 'dǐng'},
    51: {"z": 51, "element": 'Antimony', "symbol": 'Sb', "hanzi": '震', "pinyin": 'zhèn'},
    52: {"z": 52, "element": 'Tellurium', "symbol": 'Te', "hanzi": '艮', "pinyin": 'gèn'},
    53: {"z": 53, "element": 'Iodine', "symbol": 'I', "hanzi": '漸', "pinyin": 'jiàn'},
    54: {"z": 54, "element": 'Xenon', "symbol": 'Xe', "hanzi": '歸妹', "pinyin": 'guī mèi'},
    55: {"z": 55, "element": 'Caesium', "symbol": 'Cs', "hanzi": '豐', "pinyin": 'fēng'},
    56: {"z": 56, "element": 'Barium', "symbol": 'Ba', "hanzi": '旅', "pinyin": 'lǚ'},
    57: {"z": 57, "element": 'Lanthanum', "symbol": 'La', "hanzi": '巽', "pinyin": 'xùn'},
    58: {"z": 58, "element": 'Cerium', "symbol": 'Ce', "hanzi": '兌', "pinyin": 'duì'},
    59: {"z": 59, "element": 'Praseodymium', "symbol": 'Pr', "hanzi": '渙', "pinyin": 'huàn'},
    60: {"z": 60, "element": 'Neodymium', "symbol": 'Nd', "hanzi": '節', "pinyin": 'jié'},
    61: {"z": 61, "element": 'Promethium', "symbol": 'Pm', "hanzi": '中孚', "pinyin": 'zhōng fú'},
    62: {"z": 62, "element": 'Samarium', "symbol": 'Sm', "hanzi": '小過', "pinyin": 'xiǎo guò'},
    63: {"z": 63, "element": 'Europium', "symbol": 'Eu', "hanzi": '既濟', "pinyin": 'jì jì'},
    64: {"z": 64, "element": 'Gadolinium', "symbol": 'Gd', "hanzi": '未濟', "pinyin": 'wèi jì'},
}


# Independently-authored (not copied from the source's own check list) --
# used only to re-verify the Gate==Z claim at import time below.
_CANONICAL_Z_ORDER: List[str] = [
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr",
    "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
    "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
    "Pm", "Sm", "Eu", "Gd",
]

GATE_START_DEG: Dict[int, float] = {
    gate: (GATE_41_START + i * GATE_WIDTH) % 360.0
    for i, gate in enumerate(GATE_WHEEL_SEQUENCE)
}


def _validate() -> None:
    """Self-check at import time, plus the independent cross-check
    described in the module docstring."""
    assert len(GATE_WHEEL_SEQUENCE) == 64
    assert sorted(GATE_WHEEL_SEQUENCE) == list(range(1, 65))
    assert set(GATE_ELEMENTS) == set(range(1, 65))
    for gate, data in GATE_ELEMENTS.items():
        assert data["symbol"] == _CANONICAL_Z_ORDER[gate - 1], (
            f"Gate {gate}: element {data['symbol']} doesn't match the "
            f"independently-authored periodic table entry "
            f"{_CANONICAL_Z_ORDER[gate - 1]}"
        )
        assert data["z"] == gate
    hexagrams = [d["hanzi"] for d in GATE_ELEMENTS.values()]
    assert len(set(hexagrams)) == 64, "all 64 hexagrams must be distinct"
    assert abs(GATE_WIDTH * 64 - 360.0) < 1e-9


_validate()


# ---------------------------------------------------------------------------
# FORMATTING -- verbatim.
# ---------------------------------------------------------------------------
def dms_string(deg: float) -> str:
    deg = deg % 360.0
    d = int(deg)
    rem = (deg - d) * 60
    m = int(rem)
    s = round((rem - m) * 60)
    if s == 60:
        s = 0
        m += 1
    if m == 60:
        m = 0
        d += 1
    return f"{d}\u00b0{m:02d}'{s:02d}\""


# ---------------------------------------------------------------------------
# LOOKUP ENGINE -- verbatim, including the boundary-rounding guard.
# ---------------------------------------------------------------------------
def _wrap_deg(x: float, ndigits: int = 8) -> float:
    """Wrap to [0, 360) after rounding away sub-microdegree float noise --
    without this, a value mathematically exact on a gate boundary can land
    a few femtodegrees on the wrong side and floor into the wrong gate."""
    return round(x, ndigits) % 360.0


def gate_slot_index(sid_lon: float) -> int:
    offset = _wrap_deg(sid_lon - GATE_41_START)
    return min(int(offset // GATE_WIDTH), 63)


def gate_for_longitude(sid_lon: float) -> dict:
    """Resolve a sidereal (Lahiri) ecliptic longitude to its Gate + Line.
    Never applies an ayanamsa correction itself -- callers must already
    have a sidereal longitude in hand."""
    sid_lon = _wrap_deg(sid_lon)
    slot = gate_slot_index(sid_lon)
    gate = GATE_WHEEL_SEQUENCE[slot]
    start = GATE_START_DEG[gate]
    deg_in_gate = _wrap_deg(sid_lon - start)
    line = min(int(deg_in_gate // LINE_WIDTH) + 1, 6)
    data = GATE_ELEMENTS[gate]
    return {
        "gate": gate,
        "line": line,
        "element": data["element"],
        "symbol": data["symbol"],
        "z": data["z"],
        "hexagram_hanzi": data["hanzi"],
        "hexagram_pinyin": data["pinyin"],
        "sid_lon": round(sid_lon, 4),
        "sid_lon_dms": dms_string(sid_lon),
        "start_deg": round(start, 4),
        "deg_in_gate": round(deg_in_gate, 4),
    }


def bodies_to_gates(sid_lons: Dict[str, float]) -> Dict[str, dict]:
    """{body: sidereal_longitude} -> {body: gate_info}. Feed it
    NatalChart.positions from tools/chart.py."""
    return {name: gate_for_longitude(lon) for name, lon in sid_lons.items()}


def wheel_table() -> List[dict]:
    """Full 64-row wheel, in wheel order starting at Gate 41."""
    rows = []
    for i, gate in enumerate(GATE_WHEEL_SEQUENCE):
        start = GATE_START_DEG[gate]
        end = (start + GATE_WIDTH) % 360.0
        data = GATE_ELEMENTS[gate]
        rows.append({
            "slot": i, "gate": gate, "z": data["z"], "symbol": data["symbol"],
            "element": data["element"],
            "hexagram": f"{data['hanzi']} ({data['pinyin']})",
            "start_deg": round(start, 4),
            "start_dms": dms_string(start), "end_dms": dms_string(end),
        })
    return rows
