"""Source contract for the usage graph page (vague/assets/ui/index.html).

These tests read the page text, so they guard the structure the design critique asked for
(vault list first, real controls, visible failure states). They cannot prove how it renders:
check that in a browser.
"""

import re
from importlib import resources

import pytest


@pytest.fixture(scope="module")
def page() -> str:
    return resources.files("vague").joinpath("assets/ui/index.html").read_text(encoding="utf-8")


def test_sidebar_lists_obsidian_writes_before_projects_and_skills(page):
    assert page.index('id="h-vault"') < page.index('id="h-projects"') < page.index('id="h-skills"')


def test_vault_stays_reachable_when_the_sidebar_collapses(page):
    narrow_rules = page.split("@media (max-width: 760px)")[1].split("@media (prefers-reduced-motion")[0]

    assert not re.search(r"aside\s*\{[^}]*display:\s*none", narrow_rules)
    assert 'id="vault-badge"' in page


def test_sidebar_rows_are_buttons_not_clickable_divs(page):
    assert 'el("button", { type: "button", className: "chip"' in page
    assert 'el("button", { type: "button", className: "vf"' in page
    assert 'el("a",' not in page


def test_keyboard_focus_has_a_themed_ring(page):
    assert re.search(r":focus-visible\s*\{[^}]*outline:[^}]*var\(--accent\)", page)


def test_motion_has_a_reduced_motion_path(page):
    assert "@media (prefers-reduced-motion: reduce)" in page
    assert "REDUCED.matches" in page


def test_native_controls_follow_the_theme(page):
    assert re.search(r":root\s*\{[^}]*color-scheme:\s*light dark", page)
    assert "::selection" in page
    assert "caret-color" in page


def test_failed_load_names_the_problem_and_offers_a_retry(page):
    assert "Can't reach the vague server" in page
    assert 'id="retry"' in page
    assert 'id="banner-retry"' in page


def test_toast_is_announced_to_screen_readers(page):
    assert re.search(r'id="toast"[^>]*aria-live="polite"', page)


def test_search_has_a_label_and_a_results_list(page):
    assert re.search(r'<label[^>]*for="q"', page)
    assert 'id="results"' in page


def test_labels_are_not_uppercase_eyebrows(page):
    assert "text-transform: uppercase" not in page


def test_colour_has_one_meaning_per_channel(page):
    assert "EXT_HUE" not in page
    assert "#2563eb" not in page


def test_legend_uses_the_shapes_the_canvas_draws(page):
    assert "function glyph(" in page
    assert not set("●▪▣○◐") & set(page)


def test_canvas_labels_are_placed_without_overlap(page):
    assert "function drawLabels(" in page
    assert re.search(r"placed\.some\(", page)


def test_project_hues_are_capped_below_electric_saturation(page):
    assert re.search(r"hsla\(\$\{h\},(\d+)%", page)
    assert int(re.search(r"hsla\(\$\{h\},(\d+)%", page).group(1)) <= 40


def test_timeline_spends_accent_only_on_hover_and_brush(page):
    in_range_rule = re.search(r"#hist i\.in\s*\{([^}]*)\}", page).group(1)

    assert "--accent" not in in_range_rule
    assert re.search(r"#hist\.brushing i\.in[^{]*\{[^}]*var\(--accent\)", page)


def test_layer_toggles_move_onto_the_canvas_on_narrow_screens(page):
    assert "function placeLayers()" in page
    assert 'id="viewctl"' in page


def test_keyboard_shortcuts_are_listed_in_the_page(page):
    assert 'id="keys"' in page
    assert 'id="keys-btn"' in page
