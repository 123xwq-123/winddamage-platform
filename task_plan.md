# Fix single-image reupload + examples/export-button layout

## Goal
1. Restore reliable re-upload after single-image analysis (done 2026-11-14).
2. Make example thumbnails uniform size, 10 per page.
3. Make the three export buttons (导出 Markdown / 导出 JSON / 复制 JSON) equal size.

## Current Phase
Phase 3 — browser verification of examples grid + equal buttons.

## Phases
### Phase 1 — Root cause investigation (re-upload)
**Status:** complete
- Clear callback returned `""` to `gr.Image(type="filepath")`; Gradio resolved it to the
  working directory and raised `PermissionError`. Fixed with `None` (2026-11-14).

### Phase 2 — Examples / buttons (2026-11-16)
**Status:** complete
- CDP DOM probe (authenticated) showed real structure:
  `.wd-input-col .gallery > button.gallery-item > span > .container > img`,
  already paginated 10/page (Pages 1 2), widths varying with image aspect.
- TDD RED: added `test_examples_show_exactly_ten_uniform_cards_per_page`
  and `test_export_buttons_render_equal_size`; both failed as expected.
- GREEN implementation:
  - `app.py`: `gr.Examples(..., examples_per_page=10)` explicit;
    three export buttons get `elem_classes=["wd-export-btn"]`.
  - `ui_components.py`: `.wd-input-col .gallery` becomes
    `display:grid; grid-template-columns:repeat(5, 84px)`; items and images
    locked to 84x84 with `object-fit:cover`; `.wd-export-btn` gets
    `flex:1 1 0; white-space:nowrap` so all three share equal width/height.
- Full suite: 66 tests OK; UI build OK.

### Phase 3 — Browser verification
**Status:** in_progress
- CDP measurement of rendered thumbnail and button boxes + screenshot.

## Next Step
Confirm measured 84x84 thumbs (10 per page) and equal button sizes, then screenshot review.

## Decisions Made
| Decision | Rationale |
|---|---|
| `None` for cleared image value | Gradio treats `""` as a filesystem path. |
| CSS grid on real `.gallery` class | `gr.Examples` supports no `elem_classes`; probe gave exact DOM. |
| `flex:1 1 0` + nowrap for export buttons | Makes widths equal regardless of label length, stops wrapping. |

## Errors Encountered
| Error | Attempt | Resolution |
|---|---:|---|
| `PermissionError: D:\Desktop\归档` | 1 | Empty-string image output; fixed with `None`. |
| Headless Chrome `/json` empty targets | 1-2 | Use `http://localhost:9223/json/list` and wait for page target. |
