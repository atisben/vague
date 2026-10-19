# HTML Presentation Template

Reference architecture for generating slide presentations. Every presentation follows a fixed 16:9 stage model: slides are authored at 1920×1080 and the whole stage scales to fit the browser window.

## Base HTML Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Presentation Title</title>

    <!-- Fonts: use Fontshare or Google Fonts — never system fonts -->
    <link rel="stylesheet" href="https://api.fontshare.com/v2/css?f[]=...">

    <style>
        /* ===========================================
           CSS CUSTOM PROPERTIES (THEME)
           Change these to change the whole look
           =========================================== */
        :root {
            /* Colors — from chosen style preset */
            --bg-primary: #0a0f1c;
            --bg-secondary: #111827;
            --text-primary: #ffffff;
            --text-secondary: #9ca3af;
            --accent: #00ffcc;
            --accent-glow: rgba(0, 255, 204, 0.3);

            /* Typography — authored at 1920×1080 stage size */
            --font-display: 'Clash Display', sans-serif;
            --font-body: 'Satoshi', sans-serif;
            --title-size: 112px;
            --subtitle-size: 34px;
            --body-size: 28px;

            /* Spacing — authored at 1920×1080 stage size */
            --slide-padding: 72px;
            --content-gap: 32px;

            /* Animation */
            --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
            --duration-normal: 0.6s;
        }

        /* ===========================================
           BASE STYLES
           =========================================== */
        * { margin: 0; padding: 0; box-sizing: border-box; }

        /* --- PASTE viewport-base.css CONTENTS HERE --- */

        /* ===========================================
           ANIMATIONS
           Trigger via .visible class on the active slide
           =========================================== */
        .reveal {
            opacity: 0;
            transform: translateY(30px);
            transition: opacity var(--duration-normal) var(--ease-out-expo),
                        transform var(--duration-normal) var(--ease-out-expo);
        }

        .slide.visible .reveal {
            opacity: 1;
            transform: translateY(0);
        }

        /* Stagger children for sequential reveal */
        .reveal:nth-child(1) { transition-delay: 0.1s; }
        .reveal:nth-child(2) { transition-delay: 0.2s; }
        .reveal:nth-child(3) { transition-delay: 0.3s; }
        .reveal:nth-child(4) { transition-delay: 0.4s; }

        /* ... preset-specific styles ... */
    </style>
</head>
<body>
    <div class="deck-viewport">
        <main class="deck-stage" id="deckStage">
            <section class="slide title-slide active">
                <h1 class="reveal">Presentation Title</h1>
                <p class="reveal">Subtitle or author</p>
            </section>

            <section class="slide">
                <div class="slide-content">
                    <h2 class="reveal">Slide Title</h2>
                    <p class="reveal">Content...</p>
                </div>
            </section>

            <!-- More slides... -->
        </main>
    </div>

    <script>
        /* ===========================================
           SLIDE PRESENTATION CONTROLLER
           =========================================== */
        class SlidePresentation {
            constructor() {
                this.slides = document.querySelectorAll('.slide');
                this.currentSlide = 0;
                this.stage = document.getElementById('deckStage');
                this.setupStageScale();
                this.setupKeyboardNav();
                this.setupTouchNav();
                this.showSlide(0);
            }

            setupStageScale() {
                const scale = () => {
                    const factor = Math.min(window.innerWidth / 1920, window.innerHeight / 1080);
                    const x = (window.innerWidth - 1920 * factor) / 2;
                    const y = (window.innerHeight - 1080 * factor) / 2;
                    this.stage.style.transform = `translate(${x}px, ${y}px) scale(${factor})`;
                };
                scale();
                window.addEventListener('resize', scale);
            }

            setupKeyboardNav() {
                // Arrow keys, Space, Page Up/Down
            }

            setupTouchNav() {
                // Touch/swipe support for mobile
            }

            showSlide(index) {
                this.currentSlide = Math.max(0, Math.min(index, this.slides.length - 1));
                this.slides.forEach((slide, i) => {
                    slide.classList.toggle('active', i === this.currentSlide);
                    slide.classList.toggle('visible', i === this.currentSlide);
                });
            }
        }

        new SlidePresentation();
    </script>
</body>
</html>
```

## Required JavaScript Features

Every presentation must include:

1. **SlidePresentation Class** — Main controller with:
   - Keyboard navigation (arrows, space, page up/down)
   - Touch/swipe support
   - Mouse wheel navigation
   - Optional progress indicator or page count, kept outside the slide stage

2. **Stage Scaling** — For fixed 16:9 presentation behavior:
   - Keep all slides at 1920×1080 inside `.deck-stage`
   - Scale the whole stage with one transform
   - Letterbox/pillarbox as needed; never reflow slide content per device

3. **Optional Enhancements** (match to chosen style):
   - Custom cursor with trail
   - Particle system background (canvas)
   - Parallax effects
   - 3D tilt on hover
   - Magnetic buttons
   - Counter animations

4. **Inline Editing** (included by default after draft generation):
   - Edit toggle button (hidden by default, revealed via hover hotzone or `E` key)
   - Auto-save to localStorage
   - Export/save file functionality
   - See "Inline Editing Implementation" section below

## Inline Editing Implementation

Inline editing is a lightweight post-draft affordance. Do not ask the user whether they want it during the pre-generation Q&A. Include it by default unless the user explicitly asks for a locked/export-only presentation or no editing controls.

**Do NOT use CSS `~` sibling selector for hover-based show/hide.** The CSS-only approach (`edit-hotzone:hover ~ .edit-toggle`) fails because `pointer-events: none` on the toggle button breaks the hover chain: user hovers hotzone -> button becomes visible -> mouse moves toward button -> leaves hotzone -> button disappears before click.

**Required approach: JS-based hover with 400ms delay timeout.**

HTML:
```html
<div class="edit-hotzone"></div>
<button class="edit-toggle" id="editToggle" title="Edit mode (E)">✏️</button>
```

CSS (visibility controlled by JS classes only):
```css
/* Do NOT use CSS ~ sibling selector for this!
   pointer-events: none breaks the hover chain.
   Must use JS with delay timeout. */
.edit-hotzone {
    position: fixed; top: 0; left: 0;
    width: 80px; height: 80px;
    z-index: 10000;
    cursor: pointer;
}
.edit-toggle {
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.3s ease;
    z-index: 10001;
}
.edit-toggle.show,
.edit-toggle.active {
    opacity: 1;
    pointer-events: auto;
}
```

JS (three interaction methods):
```javascript
// 1. Click handler on the toggle button
document.getElementById('editToggle').addEventListener('click', () => {
    editor.toggleEditMode();
});

// 2. Hotzone hover with 400ms grace period
const hotzone = document.querySelector('.edit-hotzone');
const editToggle = document.getElementById('editToggle');
let hideTimeout = null;

hotzone.addEventListener('mouseenter', () => {
    clearTimeout(hideTimeout);
    editToggle.classList.add('show');
});
hotzone.addEventListener('mouseleave', () => {
    hideTimeout = setTimeout(() => {
        if (!editor.isActive) editToggle.classList.remove('show');
    }, 400);
});
editToggle.addEventListener('mouseenter', () => {
    clearTimeout(hideTimeout);
});
editToggle.addEventListener('mouseleave', () => {
    hideTimeout = setTimeout(() => {
        if (!editor.isActive) editToggle.classList.remove('show');
    }, 400);
});

// 3. Hotzone direct click
hotzone.addEventListener('click', () => {
    editor.toggleEditMode();
});

// 4. Keyboard shortcut (E key, skip when editing text)
document.addEventListener('keydown', (e) => {
    if ((e.key === 'e' || e.key === 'E') && !e.target.getAttribute('contenteditable')) {
        editor.toggleEditMode();
    }
});
```

### Saving and Restoring Edits

Never restore saved text by element position. A restyle or an inserted slide shifts positions, and old text lands in the wrong elements.

- Give every editable element a stable, content-derived id at generation time: `data-edit-id="s03-title"`, `data-edit-id="s03-bullet-2"`. The id never changes when the layout changes.
- Key the storage on the deck name and a version: `slides:<deck-file-name>:<DECK_VERSION>`. Set `DECK_VERSION` once in the deck's script. Bump it on every restyle (Mode D) or structural change, so edits from an older structure are ignored.
- Save a map of `data-edit-id` → `innerHTML`, and restore only ids that exist in the current deck.

```javascript
const DECK_VERSION = '1';
const STORAGE_KEY = `slides:${location.pathname.split('/').pop()}:${DECK_VERSION}`;

function saveEdits() {
    const edits = {};
    document.querySelectorAll('[data-edit-id]').forEach(el => {
        edits[el.dataset.editId] = el.innerHTML;
    });
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(edits)); } catch (e) {}
}

function restoreEdits() {
    let edits = {};
    try { edits = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); } catch (e) {}
    for (const [id, html] of Object.entries(edits)) {
        const el = document.querySelector(`[data-edit-id="${id}"]`);
        if (el) el.innerHTML = html;
    }
}
```

## Image Pipeline (Skip If No Images)

If user chose "No images" in Phase 1, skip this entirely. If images were provided, process them before generating HTML.

**Dependency:** `pip install Pillow`

### Image Processing

```python
from PIL import Image, ImageDraw

# Circular crop (for logos on modern/clean styles)
def crop_circle(input_path, output_path):
    img = Image.open(input_path).convert('RGBA')
    w, h = img.size
    size = min(w, h)
    left, top = (w - size) // 2, (h - size) // 2
    img = img.crop((left, top, left + size, top + size))
    mask = Image.new('L', (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size, size], fill=255)
    img.putalpha(mask)
    img.save(output_path, 'PNG')

# Resize (for oversized images that inflate HTML)
def resize_max(input_path, output_path, max_dim=1200):
    img = Image.open(input_path)
    img.thumbnail((max_dim, max_dim), Image.LANCZOS)
    img.save(output_path, quality=85)
```

| Situation | Operation |
|-----------|-----------|
| Square logo on rounded aesthetic | `crop_circle()` |
| Image > 1MB | `resize_max(max_dim=1200)` |
| Wrong aspect ratio | Manual crop with `img.crop()` |

Save processed images with `_processed` suffix. Never overwrite originals.

### Image Placement

**Use direct file paths** (not base64) — presentations are viewed locally:

```html
<img src="assets/logo_round.png" alt="Logo" class="slide-image logo">
<img src="assets/screenshot.png" alt="Screenshot" class="slide-image screenshot">
```

```css
.slide-image {
    max-width: 100%;
    max-height: min(50vh, 400px);
    object-fit: contain;
    border-radius: 8px;
}
.slide-image.screenshot {
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}
.slide-image.logo {
    max-height: min(30vh, 200px);
}
```

**Adapt border/shadow colors to match the chosen style's accent.** Never repeat the same image on multiple slides (except logos on title + closing).

**Placement patterns:** Logo centered on title slide. Screenshots in two-column layouts with text. Full-bleed images as slide backgrounds with text overlay (use sparingly).

---

## SVG Charts

Draw charts as inline SVG sized in stage pixels. Two rules prevent the most common rendering bugs:

- **Never use `preserveAspectRatio="none"` on an SVG that contains text.** That setting lets the SVG stretch to fill its box, so labels distort. Give the SVG a `viewBox` that matches its rendered width and height, or keep the default `xMidYMid meet`. If only a background shape must stretch, put it in its own SVG and keep the labels in HTML or a separate unstretched SVG.
- **Set chart transparency with `fill-opacity` / `stroke-opacity`, never `opacity`.** The reveal animations animate `opacity` from 0 to 1, which overrides any static `opacity` on the same element. A forecast band set to `opacity: 0.3` ends up fully opaque after the fade.

```html
<!-- Range band: transparency on fill-opacity, animation free to use opacity -->
<svg viewBox="0 0 1600 500" width="1600" height="500">
  <path class="reveal" d="M0,320 C400,280 800,260 1600,200 L1600,300 C800,360 400,380 0,400 Z"
        fill="#7AD6E5" fill-opacity="0.35"/>
  <path d="M0,360 C400,330 800,310 1600,250" fill="none" stroke="#E75D36" stroke-width="4"/>
  <text x="1590" y="240" text-anchor="end" font-size="22">Plan</text>
</svg>
```

## Code Quality

**Comments:** Every section needs clear comments explaining what it does and how to modify it.

**Accessibility:**
- Semantic HTML (`<section>`, `<nav>`, `<main>`)
- Keyboard navigation works fully
- ARIA labels where needed
- `prefers-reduced-motion` support (included in viewport-base.css)

## File Structure

Single presentations:
```
presentation.html    # Self-contained, all CSS/JS inline
assets/              # Images only, if any
```

Multiple presentations in one project:
```
[name].html
[name]-assets/
```
