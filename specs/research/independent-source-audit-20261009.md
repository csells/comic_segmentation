# Independent fixture source audit — frozen before inference

**Source inspection completed 2026-10-09 at 19:47:19 UTC.** These are evaluation
annotations only. None may enter detector prompts, automatic scene descriptions,
crop repairs or runtime decisions. All twelve complete original input PNGs were
opened directly with `view_image`; no segmentation output was inspected and no
API call, image transformation or fixture edit was made. Local SHA-256 readings
matched every input entry in the [acquisition manifest](independent-fixtures-20261009.json).
Source provenance and terms remain in the [fixture report](independent-fixtures-20261009.md).

The annotations below freeze scene identities and order, not pixel-perfect mask
boundaries. Review actual emitted crops against the original source separately.
An overview must precede the guided steps. Every target must retain its owned
artwork, caption, balloon and border-breaking content; a cropped incidental
neighbor is not automatically a defect. Extra white margin or modest incidental
neighboring material is acceptable when it preserves the target. A whole-page
fallback on a multipanel input loses segmentation coverage and is not a pass.

## Expected inventories

| Input | Expected classification / narrative inventory | Guided order |
| --- | --- | --- |
| Ubunchu 01 | Whole-page cover: one composite cover view, no narrative panel sequence | Complete cover only |
| Ubunchu 02 | 3 narrative panels | Three horizontal bands, top to bottom |
| Ubunchu 03 | 6 narrative panels | Top right; top left; tall right; middle left; bottom middle; bottom left |
| Ubunchu 04 | 7 narrative panels | Top right; top left; wide logo strip; tall lower right; three lower-left panels top to bottom |
| Ubunchu 05 | 6 narrative panels | Upper right; middle right; large upper left; bottom right; bottom middle; bottom left |
| Ubunchu 06 | 7 narrative panels | Top strip; middle right; middle center; middle left; large bottom right; bottom-left upper; bottom-left lower |
| xkcd 303 | One continuous captioned cartoon; whole-page treatment is appropriate | Caption and office scene together |
| xkcd 327 | 4 narrative panels | Left to right, including the second borderless beat |
| xkcd 1052 | 36 narrative cells | Nine rows of four, each left to right, rows top to bottom |
| Homem-Grilo section 01 | 4 narrative scenes; an optional separate title/credits preface is acceptable | Optional preface, then four scenes top to bottom |
| Homem-Grilo section 02 | 5 narrative scenes | Top to bottom |
| Homem-Grilo section 03 | 6 narrative scenes | Top to bottom |

These are twelve input units from three artist/book groups, not twelve independent
books or twelve conventional print pages. The webtoon source download chunks are
not panel boundaries: section 03 has six scenes although it was assembled from
five published source chunks.

## Ubunchu: genuine RTL controls

The directions here refer to the original Japanese artwork, without mirroring.
Numbered identities follow reading order, not the coordinates of a panel's upper
left corner. A tall panel that spans rows must remain one view.

**01 — cover.** Preserve the complete title, characters, floating computer/media
objects, upside-down figure, penguin and attribution/license block. These belong
to one cover composition; individual objects or characters are not narrative
insets. An intentional whole-page classification is correct, distinct from a
failed multipanel page being sent to fallback.

**02 — three horizontal panels.**

1. Short-haired girl presents an Ubuntu disc toward the reader.
2. Dark-haired boy and ponytailed girl react within one shared horizontal view.
3. Wider classroom action with all three characters and flying discs.

Keep the first girl's hair above the drawn top border and the correction note
between the first and second panels with the first scene. Keep the third scene's
left balloon that extends outside its rectangular frame. Two differently sized
heads in panel 2 are not two separate camera views.

**03 — six panels.**

1. Top right: angry boy speaking and gesturing.
2. Top left: ponytailed girl holding a disc and gesturing.
3. Tall right-hand panel beneath them: the computer tower and accompanying text.
4. Middle left: smiling short-haired girl raises one finger amid flying discs.
5. Bottom middle: the explanatory Linux/Windows/Mac character diagram.
6. Bottom left: the short-haired girl is startled as a disc crosses overhead.

The diagram is one explanatory panel, not three independently narrated face
insets. The tall computer panel precedes both lower-left rows; sorting only by
box top edges or reading all the way down the left column would be wrong.

**04 — seven panels.**

1. Top right: the short-haired girl tumbles back while the other two react.
2. Top left: close-up of her smiling and holding the disc.
3. Full-width black Ubuntu logo/boot strip with dialogue.
4. Tall lower right: all three at the computers; the ponytailed girl is foreground.
5. Upper of the three lower-left panels: close-up of the girl typing, with the
   other two behind and large typing sound effects along the bottom.
6. Middle lower-left panel: tighter close-up of her eye/face with dialogue.
7. Bottom left: boy turns toward her while the short-haired girl sits at the desk.

The logo strip is an intentional illustrated screen close-up and retains its
dialogue plus the correction note below it. Panel 4 is one tall classroom view,
not three strips corresponding to the left-hand stack. Keep lettering that
crosses the border of panel 5.

**05 — six panels.**

1. Upper right: a hand points toward text on the computer display.
2. Right below it: the ponytailed girl makes a dark, dramatic expression.
3. Large upper left: the wizard/fantasy illustration and explanatory dialogue.
4. Bottom right: her profile and continuing dialogue.
5. Bottom middle: the short-haired girl announces success; her companions react.
6. Bottom left: boy and short-haired girl discuss how she did it.

The fantasy illustration is one composition, including its background figures,
monsters and labels. They are not separately framed narrative views. Read both
small upper-right panels before the large left panel, then the bottom row RTL.

**06 — seven panels.**

1. Top strip: the short-haired girl reads a magazine while the ponytailed girl
   reacts behind her.
2. Middle right: network configuration interface and dialogue.
3. Middle center: updates/package-manager interface and dialogue.
4. Middle left: codec installation interface and dialogue.
5. Large bottom right: the trio at the monitor, with the boy smiling broadly.
6. Upper bottom-left panel: the short-haired girl's profile as she speaks.
7. Lower bottom-left panel: the ponytailed girl's embarrassed smiling close-up.

UI rows, icons and window borders are internal content, not panel dividers. Small
floating reaction heads around panel 5 are decorative content within that same
view. Preserve them, but do not turn them into extra reader steps.

## xkcd: captions, borderless beat and dense grid

**303.** One captioned office cartoon. The large text above the office establishes
the joke and belongs with the scene. The horizontal line under the heading does
not create another narrative moment. Preserve the doorway conversation, both
chair riders, chairs and complete top caption.

**327.** Four LTR phone-conversation beats: school reports trouble; mother asks
what happened; discussion of the son's problematic name; consequences and reply.
The second beat has no complete rectangular outline but is still a separate
illustrated view. Keep all text in each beat, including the text below/alongside
the characters. Do not merge the first and second beats because one border is absent.

**1052.** Exactly nine rows of four narrative cells. The following compact labels
fix row-major order without requiring dialogue transcription:

| Row | Left to right |
| --- | --- |
| 1 | Philosophy; mathematics/physics; business; chemistry |
| 2 | Mystery major; art history; communications; underwater basket weaving |
| 3 | Biology; psychology/sociology; difficulty choosing; undecided refrain |
| 4 | Seismology; theology; computer science parentheses; virology |
| 5 | Nonstop fighting; geography; physics/bongo scene; physics-to-engineering diagram |
| 6 | History repetition; teaching; irreparable four-year plans; undecided refrain |
| 7 | Astronomy; agronomy; herpetology; gastroenterology |
| 8 | Premed; poetry; forensic science/television logo; meta-academic epidemiology |
| 9 | Economics; reply about that label; comparison of choices; final undecided refrain |

Some cells place their caption above a smaller art rectangle or omit one or more
outer frame edges. The associated caption must accompany that cell. Internal
diagram elements and multiple characters inside a cell are not additional panels.
The overall song title is a heading, not a 37th narrative scene; its presence in
the complete-page overview is sufficient, and retaining it with the first crop is
also acceptable. Neither alternative permits dropping any of the 36 cell captions.

## Homem-Grilo: tall sections and detached content

Each section is read top to bottom. Large white gaps are intentional; balloons
and tails in those gaps must not be discarded as background. Within a scene,
Portuguese dialogue follows LTR conventions.

**Section 01 — four narrative scenes.** Exterior establishing view of the bar;
larger interior view with patrons and the seated friends; food handed across the
counter; the friends at their table celebrating the arrival of the food. The
location caption belongs to the exterior. Both detached balloons around the
counter scene must remain complete, including the one below its frame. The final
scene's balloon extends above the frame.

The title, creators and license occupy their own large introduction area before
the four scenes. Two predeclared acceptable treatments are (a) four narrative
steps after the full-section overview, or (b) a dedicated non-narrative title/
credits step followed by those same four scenes. Thus four or five total guided
steps can be acceptable here, but the narrative inventory is four either way.
The title is not grounds for classifying this entire multipanel section as a cover.

**Section 02 — five scenes.** Glasses-wearing friend receives a poured drink;
seated dark-haired friend responds; wider street/bar view with the women at right
and the seated friends at left; narrow two-friend conversation against pink;
the dark-haired friend stands and declares his intention while the other reacts.

The third is one deep, continuous view, not separate panels for the women and
the seated friends. The fourth has two high, detached balloons with long tails.
The fifth has a detached top balloon and a standing figure extending beyond its
frame at the left and bottom; retain all artwork actually visible in the source.
Art already cut off by the source edge does not require invented completion.

**Section 03 — six scenes.** Dark-haired friend approaches the women; a yellow-shirted
man barges in, bumping him; the yellow-shirted man speaks while the woman questions
him; he poses and introduces himself; he invites her and she replies; she points
to the dark-haired friend and the group reacts.

Keep the second scene's impact lettering and motion stroke reaching left of its
frame. Preserve all joined/stacked balloons above the fourth and fifth scenes,
and both detached balloons above the final scene. No gap, balloon group or
download-chunk seam is an extra scene.

## Frozen source hashes

Paths below are relative to
`validation-artifacts/segmentation-iteration-20261008/independent-fixtures-20261009/inputs/`.

| Input path | SHA-256 |
| --- | --- |
| `ubunchu01-ja/ubunchu01_01.png` | `46edc928a569782199565c0f4788c04cf1bfce401073788131c64c7a48a11735` |
| `ubunchu01-ja/ubunchu01_02.png` | `d5737394c163cbc46348582f8684e4c38b565765eaaa77828d370a5100fcbbee` |
| `ubunchu01-ja/ubunchu01_03.png` | `0415128bd10a53b9964851c62cf54ec69ce73c805719bd042ca9e5c3dcabf8a3` |
| `ubunchu01-ja/ubunchu01_04.png` | `bc5a90b6952e45f11f9d6de80195cef48d2c0dee211e6071521001dd0848abe3` |
| `ubunchu01-ja/ubunchu01_05.png` | `5dfb6ed69c9e9ad0402707ee60a038c7d1d1af0124f1bb169b07afefad705cba` |
| `ubunchu01-ja/ubunchu01_06.png` | `18ddf8669a843afe5545ec4d0f8a4e95bcf7dfdb511f1cef610af48a77cc4743` |
| `xkcd/xkcd-0303.png` | `1489aef471a4ed7cda5e1c69bf9ce9d51395bd2e781346216f025e208c95756b` |
| `xkcd/xkcd-0327.png` | `0c7b09d66d4dcf0b315bab40833a8b876702bec2d15c826b86c351a7b4fe1c50` |
| `xkcd/xkcd-1052.png` | `880302480a4a3f5553e8f943c3c68065fa36499ed0eca29009af641318e8bc07` |
| `homem-grilo/homemgrilo-hq013pg01-webtoon-section.png` | `5c9699f3638e47ee965c2b49bcf2e6e0d5ee8a192fe4217e9d94c6f9a1cd9611` |
| `homem-grilo/homemgrilo-hq013pg02-webtoon-section.png` | `fc85fb3f4a708eac59bbb47c279b2b6d10ccbe8e2e910edaac489d071ef15298` |
| `homem-grilo/homemgrilo-hq013pg03-webtoon-section.png` | `d7e8cb1c3bc4b8422ecc754904e91cf87a4b79affd7292a337d167d3f573552c` |

## Qualification limits

This source audit does not certify inferred polygons, exact viewport edges or
OCR. Border thickness and antialiased fringes admit small geometric differences;
the acceptable alternatives above do not excuse missing visible target art or
text. All source views are presently countable without an unresolved binary
inventory label. The one explicit count alternative is the optional non-narrative
Homem-Grilo title preface. If later source review discovers a genuine ambiguity,
record an amendment with its reason and timestamp and quarantine that scoring
claim; never silently adjust the expected answer after seeing an output.

These annotations were authored by `verifier_protocol` from source inspection.
A second review of the six xkcd/Homem-Grilo sources was requested but had not
completed when this initial audit was written. Root will independently inspect
the actual emitted crops; that later output review is a separate validation step.
