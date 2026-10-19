"""The Obsidian Excalidraw plugin stores drawings with LZString.compressToBase64."""

import pytest

from vague.sdk.core.lzstring import compress_to_base64, decompress_from_base64

# Reference values produced by the lz-string JS library (npm lz-string 1.5).
JS_VECTORS = [
    ("hello world", "BYUwNmD2AEDukCcwBMg="),
    ('{"type":"excalidraw","elements":[]}', "N4IgLgngDgpiBcIYA8DGBDANgSwCYCd0B3EAGiUxgFsYA7MAZwQG0BdAXyA="),
    ("é → ≈ 🚀 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "JcAkSYQoEkQovBuAF7ICGyWrejmg"),
]


@pytest.mark.parametrize(("plain", "compressed"), JS_VECTORS)
def test_compress_matches_js_library(plain, compressed):
    assert compress_to_base64(plain) == compressed


@pytest.mark.parametrize(("plain", "compressed"), JS_VECTORS)
def test_decompress_reads_js_library_output(plain, compressed):
    assert decompress_from_base64(compressed) == plain


def test_round_trip_preserves_long_unicode_text():
    plain = '{"text":"Fri 16:30 → Sat ≈ NULL"}' * 500
    assert decompress_from_base64(compress_to_base64(plain)) == plain


def test_decompress_ignores_line_breaks_in_stored_data():
    compressed = JS_VECTORS[1][1]
    wrapped = compressed[:20] + "\n" + compressed[20:]
    assert decompress_from_base64(wrapped) == JS_VECTORS[1][0]
