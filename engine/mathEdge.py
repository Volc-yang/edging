"""
Edge World - Foundational Transformation Laws for the I Ching Model

This module defines the data structures and transformation rules for the 8 trigrams and 64 hexagrams,
which form the mathematical basis of the Edge World engine.

The representation is based on standard binary encoding (Yin=0, Yang=1) from bottom to top.

It includes:
- Data representation for Trigrams and Hexagrams.
- Houtian Bagua (后天八卦) arrangement.
- Core hexagram transformations:
  - Bian Gua (变卦): Changing specific lines.
  - Zong Gua (综卦): Inverting the hexagram (upside down).
  - Cuo Gua (错卦): Inverting all lines (Yin <-> Yang).
- Jing Fang's Eight Palaces (京房八宮) transformations:
  - Lihun Gua (离魂卦 / 游魂卦): The "Wandering Soul" hexagram.
  - Guihun Gua (归魂卦): The "Returning Soul" hexagram.
- Integration with classical Chinese texts from 'yijing_text.json'.
"""

import functools
import json
from pathlib import Path
from typing import Dict, List, Optional

# --- Text Data Loading ---

@functools.lru_cache(maxsize=1)
def load_yijing_text():
    """Loads the I Ching textual data from the yijing_text.json file."""
    json_path = Path(__file__).parent / "yijing_text.json"
    if not json_path.exists():
        return {}
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# --- Data Representation ---

# The 8 Trigrams based on Fu Xi's "Early Heaven" sequence, which provides a natural binary ordering.
# Binary value is read from bottom line (LSB) to top line (MSB). Yin=0, Yang=1.
TRIGRAMS = {
    'kun':  {'name': '坤', 'symbol': '☷', 'value': 0b000},  # 0
    'gen':  {'name': '艮', 'symbol': '☶', 'value': 0b001},  # 1
    'kan':  {'name': '坎', 'symbol': '☵', 'value': 0b010},  # 2
    'xun':  {'name': '巽', 'symbol': '☴', 'value': 0b011},  # 3
    'zhen': {'name': '震', 'symbol': '☳', 'value': 0b100},  # 4
    'li':   {'name': '离', 'symbol': '☲', 'value': 0b101},  # 5
    'dui':  {'name': '兑', 'symbol': '☱', 'value': 0b110},  # 6
    'qian': {'name': '乾', 'symbol': '☰', 'value': 0b111},  # 7
}
TRIGRAM_BY_VALUE = {v['value']: v for k, v in TRIGRAMS.items()}

# Houtian Bagua (后天八卦) "Later Heaven" spatial and numerological arrangement.
HOUTIAN_BAGUA = {
    'kan':  {'direction': 'N',  'number': 1, 'element': 'Water',   **TRIGRAMS['kan']},
    'kun':  {'direction': 'SW', 'number': 2, 'element': 'Earth',   **TRIGRAMS['kun']},
    'zhen': {'direction': 'E',  'number': 3, 'element': 'Thunder', **TRIGRAMS['zhen']},
    'xun':  {'direction': 'SE', 'number': 4, 'element': 'Wind',    **TRIGRAMS['xun']},
    # Center is 5
    'qian': {'direction': 'NW', 'number': 6, 'element': 'Heaven',  **TRIGRAMS['qian']},
    'dui':  {'direction': 'W',  'number': 7, 'element': 'Lake',    **TRIGRAMS['dui']},
    'gen':  {'direction': 'NE', 'number': 8, 'element': 'Mountain',**TRIGRAMS['gen']},
    'li':   {'direction': 'S',  'number': 9, 'element': 'Fire',    **TRIGRAMS['li']},
}


class Hexagram:
    """Represents one of the 64 hexagrams as a 6-bit integer, with integrated text access."""

    def __init__(self, value: int):
        """
        Initializes a Hexagram from a 6-bit integer value (0-63).
        The lower 3 bits represent the lower trigram, and the upper 3 bits
        represent the upper trigram.
        """
        if not 0 <= value <= 63:
            raise ValueError("Hexagram value must be between 0 and 63.")
        self.value = value

    @classmethod
    def from_string(cls, binary_str: str) -> 'Hexagram':
        """Creates a Hexagram from a 6-digit binary string (e.g., "111000")."""
        if len(binary_str) != 6 or not all(c in '01' for c in binary_str):
            raise ValueError("Input must be a 6-digit binary string.")
        # Reverse string because text format is top-to-bottom, but our binary is bottom-to-top
        return cls(int(binary_str[::-1], 2))

    @classmethod
    def from_trigrams(cls, upper_trigram: int, lower_trigram: int) -> 'Hexagram':
        """Creates a Hexagram from upper and lower trigram values."""
        if not (0 <= upper_trigram <= 7 and 0 <= lower_trigram <= 7):
            raise ValueError("Trigram values must be between 0 and 7.")
        return cls((upper_trigram << 3) | lower_trigram)

    # --- Core Properties ---

    @property
    def upper(self) -> Dict:
        """Returns the dictionary for the upper trigram."""
        return TRIGRAM_BY_VALUE[self.value >> 3]

    @property
    def lower(self) -> Dict:
        """Returns the dictionary for the lower trigram."""
        return TRIGRAM_BY_VALUE[self.value & 0b111]

    @property
    def lines(self) -> List[int]:
        """Returns the six lines as a list of integers [bottom, ..., top]."""
        return [(self.value >> i) & 1 for i in range(6)]

    def to_binary_string(self) -> str:
        """Returns the 6-bit binary string representation (bottom to top)."""
        return f"{self.value:06b}"

    # --- Textual Data Properties ---

    @property
    def text_key(self) -> str:
        """Returns the yijing_text.json key: upper trigram bits followed by lower trigram bits."""
        return f"{self.value >> 3:03b}{self.value & 0b111:03b}"

    @property
    def text_data(self) -> Optional[Dict]:
        """Returns all textual data for this hexagram from the JSON file."""
        yijing_data = load_yijing_text()
        return yijing_data.get(self.text_key)

    @property
    def name(self) -> Optional[str]:
        """Returns the Chinese name of the hexagram."""
        data = self.text_data
        return data['name'] if data else None

    @property
    def symbol(self) -> Optional[str]:
        """Returns the Unicode hexagram symbol."""
        data = self.text_data
        return data['symbol'] if data else None

    @property
    def sequence(self) -> Optional[int]:
        """Returns the canonical sequence number in the King Wen order."""
        data = self.text_data
        return data['sequence'] if data else None

    @property
    def judgment(self) -> Optional[Dict]:
        """Returns the judgment text and commentary (卦辞 and 彖传)."""
        data = self.text_data
        return data['judgment'] if data else None

    @property
    def image(self) -> Optional[Dict]:
        """Returns the Great Image text (大象)."""
        data = self.text_data
        return data['image'] if data else None

    def line(self, position: int) -> Optional[Dict]:
        """
        Returns the text data for a specific line.
        Position is 1-6 from bottom to top.
        For Qian and Kun, position 7 accesses the special "Yong" line.
        """
        if not 1 <= position <= 7:
            raise ValueError("Line position must be between 1 and 7.")
        data = self.text_data
        if not data or 'lines' not in data:
            return None
        
        for line_data in data['lines']:
            if line_data['line_number'] == position:
                return line_data
        return None

    # --- Transformations ---

    def change(self, positions: List[int]) -> 'Hexagram':
        """
        Calculates the Bian Gua (变卦) by changing lines at given positions.
        Positions are 1-6 from bottom to top. A changed line becomes its opposite.
        """
        mask = 0
        for pos in positions:
            if not 1 <= pos <= 6:
                raise ValueError("Line position must be between 1 and 6.")
            mask |= (1 << (pos - 1))
        return Hexagram(self.value ^ mask)

    def overturn(self) -> 'Hexagram':
        """
        Calculates the Zong Gua (综卦), the overturned hexagram.
        This transformation flips the hexagram upside down. The 1st line
        becomes the 6th, 2nd becomes 5th, etc.
        """
        reversed_val = 0
        temp_val = self.value
        for _ in range(6):
            reversed_val <<= 1
            reversed_val |= (temp_val & 1)
            temp_val >>= 1
        return Hexagram(reversed_val)

    def interchange(self) -> 'Hexagram':
        """
        Calculates the Cuo Gua (错卦), the interchanged hexagram.
        This transformation inverts every line (Yin becomes Yang, Yang becomes Yin).
        It represents the opposite perspective or underlying potential.
        """
        return Hexagram(self.value ^ 0b111111)

    def __repr__(self) -> str:
        name_str = f" {self.name}" if self.name else ""
        upper_s = self.upper['symbol']
        lower_s = self.lower['symbol']
        # Binary string reversed to match top-down visual representation
        binary_view = self.to_binary_string()[::-1]
        return f"<Hexagram {self.value:02d}{name_str} ({binary_view}) | {upper_s} / {lower_s}>"

# --- Jing Fang's Eight Palaces (京房八宮) Logic ---

@functools.lru_cache(maxsize=1)
def _build_eight_palaces() -> Dict[int, List[Dict[str, Hexagram]]]:
    """
    Generates the structure of the Eight Palaces system.
    Each palace contains a sequence of 8 hexagrams derived from a pure trigram.
    """
    palaces = {}
    # Palace heads are pure trigrams (Qian, Zhen, Kan, Gen, Kun, Xun, Li, Dui)
    palace_heads = [0b111, 0b100, 0b010, 0b001, 0b000, 0b011, 0b101, 0b110]

    for head_trigram_val in palace_heads:
        palace = []
        # 1. Palace Head (本宫卦)
        current_hex = Hexagram.from_trigrams(head_trigram_val, head_trigram_val)
        palace.append({'gen': 0, 'name': 'Palace Head', 'hex': current_hex})

        # 2. Generations 1-5 (一世卦 to 五世卦)
        for i in range(5):
            current_hex = current_hex.change([i + 1])
            palace.append({'gen': i + 1, 'name': f'{i+1}-Gen', 'hex': current_hex})

        # 3. Wandering Soul (游魂卦)
        current_hex = palace[5]['hex'].change([4])
        palace.append({'gen': 6, 'name': 'Wandering Soul', 'hex': current_hex})

        # 4. Returning Soul (归魂卦)
        youhun_upper = current_hex.upper['value']
        guihun_hex = Hexagram.from_trigrams(youhun_upper, head_trigram_val)
        palace.append({'gen': 7, 'name': 'Returning Soul', 'hex': guihun_hex})

        palaces[head_trigram_val] = palace
    return palaces

EIGHT_PALACES = _build_eight_palaces()
HEXAGRAM_TO_PALACE_MAP = {
    entry['hex'].value: (head_val, palace)
    for head_val, palace in EIGHT_PALACES.items()
    for entry in palace
}

def find_palace(hexagram: Hexagram) -> Optional[Dict]:
    """Finds the palace a given hexagram belongs to."""
    if hexagram.value not in HEXAGRAM_TO_PALACE_MAP:
        return None
    head_val, palace_list = HEXAGRAM_TO_PALACE_MAP[hexagram.value]
    palace_head_trigram = TRIGRAM_BY_VALUE[head_val]
    return {
        'palace_head_trigram': palace_head_trigram,
        'palace_sequence': palace_list
    }

def get_lihun(hexagram: Hexagram) -> Optional[Hexagram]:
    """
    Finds the Lihun Gua (离魂卦), or "Wandering Soul" hexagram, for the
    palace that the given hexagram belongs to.
    """
    palace_info = find_palace(hexagram)
    if not palace_info:
        return None
    return palace_info['palace_sequence'][6]['hex']

def get_guihun(hexagram: Hexagram) -> Optional[Hexagram]:
    """
    Finds the Guihun Gua (归魂卦), or "Returning Soul" hexagram, for the
    palace that the given hexagram belongs to.
    """
    palace_info = find_palace(hexagram)
    if not palace_info:
        return None
    return palace_info['palace_sequence'][7]['hex']


if __name__ == '__main__':
    # --- Example Usage ---
    print("--- Textual Data Integration ---")
    h_qian = Hexagram.from_string("111111") # ䷀
    h_kun = Hexagram.from_string("000000") # ䷁
    
    print(f"Loaded Hexagram: {h_qian}")
    print(f"Name: {h_qian.name}")
    print(f"Judgment: {h_qian.judgment['text']}")
    print(f"Image: {h_qian.image['text']}")
    print(f"Line 1 Text: {h_qian.line(1)['text']}")
    print("-" * 20)
    print(f"Loaded Hexagram: {h_kun}")
    print(f"Name: {h_kun.name}")
    print(f"Line 6 Text: {h_kun.line(6)['text']}")
    print(f"Special 'Yong' line: {h_kun.line(7)['text']}")
    
    # --- Verify a hexagram without text data ---
    h_pi = Hexagram.from_string("111000") # ䷋, should have no text data yet
    print("-" * 20)
    print(f"Loaded Hexagram: {h_pi}")
    print(f"Name: {h_pi.name}") # Should be None
    print(f"Judgment: {h_pi.judgment}") # Should be None

    print("\n--- Basic Transformations (Verification) ---")
    h_zong = h_pi.overturn()
    print(f"Original for Overturn: {h_pi}")
    print(f"Overturned (Zong Gua): {h_zong}")

    print("\n--- Palace System (Verification) ---")
    palace = find_palace(h_pi)
    if palace:
        head_name = palace['palace_head_trigram']['name']
        print(f"{h_pi.name or h_pi.value} belongs to the Palace of {head_name}")
