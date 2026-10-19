"""Port of LZString compressToBase64 / decompressFromBase64 (pieroxy/lz-string).

The Obsidian Excalidraw plugin stores drawings in this format. The algorithm works on
UTF-16 code units, so strings are converted to and from UTF-16 to match the JS output
for characters outside the Basic Multilingual Plane.
"""

from __future__ import annotations

from collections.abc import Callable

_KEY_BASE64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
_BASE64_INDEX = {char: i for i, char in enumerate(_KEY_BASE64)}


def _to_units(text: str) -> list[str]:
    raw = text.encode("utf-16-le")
    return [chr(int.from_bytes(raw[i : i + 2], "little")) for i in range(0, len(raw), 2)]


def _from_units(units: list[str]) -> str:
    raw = b"".join(ord(u).to_bytes(2, "little") for u in units)
    return raw.decode("utf-16-le", errors="surrogatepass")


def _compress(units: list[str], bits_per_char: int, get_char: Callable[[int], str]) -> str:
    dictionary: dict[str, int] = {}
    to_create: set[str] = set()
    w = ""
    enlarge_in = 2
    dict_size = 3
    num_bits = 2
    out: list[str] = []
    val = 0
    position = 0

    def write_bits(value: int, count: int) -> None:
        nonlocal val, position
        for _ in range(count):
            val = (val << 1) | (value & 1)
            if position == bits_per_char - 1:
                position = 0
                out.append(get_char(val))
                val = 0
            else:
                position += 1
            value >>= 1

    def emit(token: str) -> None:
        nonlocal enlarge_in, num_bits
        if token in to_create:
            code = ord(token[0])
            if code < 256:
                write_bits(0, num_bits)
                write_bits(code, 8)
            else:
                write_bits(1, num_bits)
                write_bits(code, 16)
            enlarge_in -= 1
            if enlarge_in == 0:
                enlarge_in = 2**num_bits
                num_bits += 1
            to_create.discard(token)
        else:
            write_bits(dictionary[token], num_bits)
        enlarge_in -= 1
        if enlarge_in == 0:
            enlarge_in = 2**num_bits
            num_bits += 1

    for c in units:
        if c not in dictionary:
            dictionary[c] = dict_size
            dict_size += 1
            to_create.add(c)
        wc = w + c
        if wc in dictionary:
            w = wc
            continue
        emit(w)
        dictionary[wc] = dict_size
        dict_size += 1
        w = c

    if w:
        emit(w)
    write_bits(2, num_bits)

    while True:
        val <<= 1
        if position == bits_per_char - 1:
            out.append(get_char(val))
            break
        position += 1
    return "".join(out)


def _decompress(length: int, reset_value: int, get_next: Callable[[int], int]) -> list[str]:
    dictionary: dict[int, list[str]] = {0: [], 1: [], 2: []}
    enlarge_in = 4
    dict_size = 4
    num_bits = 3
    data_val = get_next(0)
    data_position = reset_value
    data_index = 1

    def read_bits(count: int) -> int:
        nonlocal data_val, data_position, data_index
        bits = 0
        power = 1
        for _ in range(count):
            resb = data_val & data_position
            data_position >>= 1
            if data_position == 0:
                data_position = reset_value
                data_val = get_next(data_index)
                data_index += 1
            if resb:
                bits |= power
            power <<= 1
        return bits

    first = read_bits(2)
    if first == 2:
        return []
    w = [chr(read_bits(8 if first == 0 else 16))]
    dictionary[3] = w
    result = list(w)

    while True:
        if data_index > length:
            return result
        code = read_bits(num_bits)
        if code in (0, 1):
            dictionary[dict_size] = [chr(read_bits(8 if code == 0 else 16))]
            code = dict_size
            dict_size += 1
            enlarge_in -= 1
        elif code == 2:
            return result
        if enlarge_in == 0:
            enlarge_in = 2**num_bits
            num_bits += 1
        if code in dictionary:
            entry = list(dictionary[code])
        elif code == dict_size:
            entry = w + [w[0]]
        else:
            raise ValueError("Corrupt LZString data")
        result.extend(entry)
        dictionary[dict_size] = w + [entry[0]]
        dict_size += 1
        enlarge_in -= 1
        w = entry
        if enlarge_in == 0:
            enlarge_in = 2**num_bits
            num_bits += 1


def compress_to_base64(text: str) -> str:
    out = _compress(_to_units(text), 6, lambda i: _KEY_BASE64[i])
    return out + "=" * (-len(out) % 4)


def decompress_from_base64(data: str) -> str:
    data = "".join(data.split())
    return _from_units(_decompress(len(data), 32, lambda i: _BASE64_INDEX[data[i]] if i < len(data) else 0))
