> 2026-10-10 update: V31 passed five actual CLI/source/crop/browser positives,
> but failed the deliberately clipped-art N2 control. Its native Luna screen
> scored clipping 0.0 and skipped stronger verification; the G inventory guard
> correctly counted all eight scenes without establishing crop extent. Stop
> independent/full-book expansion until a generic extent-screen correction passes
> the frozen controls and actual E2E. Global used/held is $54.723719/$100 after
> 12 new requests costing $1.014537. Stable Build10 and production Rust are unchanged.

# V30 development regression results

**Policy qualification stopped:** the later N1 missing-scene control was harmfully
accepted by unchanged V30. Preserve all passing outputs below as individual-page
evidence; they do not establish a reliable automatic completeness gate. N2 was not
run. A generic source-completeness fix is required before the independent screen or
full257 qualification. Globalusedheld after this control is$52.277442; eight new
native calls cost$0.002667, with six cached continuity checks.


The later generic completeness screen G passes all 11 root-reviewed cases:
three deliberate omissions and eight intact outputs. Earlier variants remain
preserved failures: they missed an ordinary omission, combined radial scenes,
split a continuous montage or identified the wrong missing view. G retains prior
source uncertainty, clarifies authored panel separation and verifies claimed
omissions with an independent stronger mapping. Its three new requests cost
$0.262626; 23 requests were cached. Global used or held is $53.709182; the shared
control envelope retains 45 requests / $1.434407. Actual V31 converter integration
is pending; frozen V30 and its failed omission control remain unchanged. See the
[source-completeness results](source-completeness-guard-results-20261009.md).

These are actual automatic conversions of selected pages from the original full 257-page PDF, using real preceding-page context and the immutable `automatic-source-ownership-v30` candidate. Root personally checks the source and every selected crop before dispatching the next page. Those review records are evaluation evidence; the converter does not read them. This development anthology is not an independent benchmark.

| Original page | Selected panels | Detector tiers / repair rounds | Root crop review | Reader playback | New requests / incremental cost |
| --- | ---: | --- | --- | --- | --- |
| 57 | 13 | Sol-low, Sol-high, Astra / 2 | Pass; curved viewports include neighboring art | Pass; overview + 13 + end, real catalog route | 34 / $1.155186 after the preserved V29 run |
| 150 | 3 | Sol-low, Sol-high, Astra / 0 | Pass; complete bouquet belongs to lower scene | Pass; overview + 3 + end, real catalog route | 17 / $0.451539 |
| 149 | 4 | Sol-low, Sol-high / 0 | Pass; full outer scene and separate inset, correct order | Pass; overview + 4 + end | 12 / $0.230433 |
| 36 | 7 | Sol-low, Sol-high, Astra / 0 | Pass; overlapping opening scene and complete courtyard/background views | Pass; overview + 7 + end | 38 / $1.036300 |
| 61 | 5 | Sol-low, Sol-high / 0; explicit transport recovery | Pass; all five selected crop bytes match personally reviewed diagnostics | Pass; overview + 5 + end | Original11 + recovery4 / $1.240970 aggregate used or held, including retained $1 |
| 144 | 2 | Sol-low, Sol-high / 0 | Pass; both montage scenes, overlapping figures and captions complete | Pass; overview + 2 + end | 5 / $0.023667 |
| 56 | 8 | Sol-low / 0 | Pass; introduction, two rows of three and eyes strip complete | Pass; overview + 8 + end | 16 / $0.003560 |
| 100 | 5 | Sol-low / 0 | Pass; dark-bordered scenes, balloons and glowing figures complete | Pass; overview + 5 + end | 10 / $0.002536 |
| 205 | 10 | Sol-low, Sol-high, Astra / 0; bounded scheduling continuation | Pass; all accepted crops match exact personally reviewed diagnostic bytes | Pass; overview + 10 + end | Original47 + continuation16 / $1.591183; all settled |

Source149 reused two responses and completed in83.269seconds. All12 new reservations settled. Source57 and150 have their own detailed [radial-page report](actual-source57-v30-validation-20261009.md) and [bouquet report](actual-source150-v30-validation-20261009.md). These measured costs/times include cache reuse and are not cold-run estimates.

At the source149 terminal, global used/held is **$47.455132 of $100**. The existing V29/V30 regression suite retains159requests/$4.603800 under its240request/$20 ceiling; older unknown and explicitly rejected quota reservations remain held. Later accounting belongs to the shared ledger and handoff.

Source149's CBZ SHA256 is `5c9c22cd4d1497f4332fe19252d2f7258a6b026a2e6d3c9c4784ad3bcadc6ca3`; selected candidate `e3bf1e924f483c1efc73970df174f9019a7ceab64a6f021ecb9374bd352169aa`; source JPEG `8fdb3a8658369f5b69a719770d982e2fc23ef39f85f926394143c5caa2f4680b`. Root's review receipt is `dc25c544d2e0e29c3de9ef6b7cd02add54f8648d1f18fff22dee953ddc2072cd`, retained alongside all four exact crops and converter records in `validation-artifacts/segmentation-iteration-20261008/actual-v30-source149-accepted-20261009/`.

Source149 browser playback passed on frozen reader8084: all five screenshots personally inspected, exact source/geometry binding, centered containment and zero exceptions. Its verified19-file export is `reader-v30-source149-20261009/actual-v30-source149-browser-evidence.tgz`,1511222bytes, SHA256 `357ba5c5d18c5fb1607f71952bde71b852286dbe7fd2aa41d813dd6684c3a1d3`. The phone catalog remains the two57/150 examples.

At source36 terminal, global used/held is **$48.491432/$100**, suite197requests/$5.640100. All38new reservations settled. The measured case took457.710seconds with3cache hits. Root reviewed all7exact crops; all seven scenes, their order and owned art were complete. Full149/36evidence is preserved in the verified archive named in the handoff.

The [source36 rejection audit](source36-v30-rejection-audit-20261009.md) confirms a real wall/ground strip was missing from the rejected Sol-high crop3; Astra restores it. Actual reader playback passed overview+7frames+end with all8screenshots inspected and zero exceptions. Its22-file browser export is2723841bytes, SHA256 `d95c9a4267d249e914b435f06682dfafed82222ad539985b4f7336ea34e7c1a9`.

All nine individual development cases and prefix1–6 now pass root crop review. Four-format panelized conversion and its actual80-step browser playback also pass. The omission-gate correction, independent books/RTL and requested all257 sequential qualification remain open. The known target10 verifier false positive, older missing-description failure, and conditional routing limitations remain documented; these passes do not establish universal correctness. Stable Build10 and production Rust remain untouched.

Source61 stopped on HTTP503 from Decisions; ten new requests settled to$0.173076 and the failed request retains its$1hold. Global used/held is$49.664508, suite208/$6.813176. The terminal is preserved, with explicit bounded transport recovery in preparation and no retry dispatched at this checkpoint. Root diagnostic review is not automatic acceptance.

The sole source61 recovery succeeded after transport tests, exact cache proof and root readiness. Fournewrequests cost$0.067894 with13cache hits in23.879seconds. Automatic acceptance selected the same five personally reviewed crop hashes; browser playback passed overview+5/end with all six screenshots personally inspected and zero exceptions. Global used/held is now$49.732402; suite212/$6.881070. The original503terminal/$1hold remain preserved.

Source144 passed automatic conversion and root review of its full source and both exact selected crops. It preserves the ballroom and proposal as two horizontal montage scenes, without splitting the overlapping figures. All captions, silhouettes, hands and dresses remain complete. Five new reservations settled to $0.023667; two responses were cached, and the run took 28.259 seconds. Global used/held is $49.756069; the same suite has 217 requests/$6.904737. CBZ SHA256 `07656b151c6b332ff635da6da1f533c0ebdec6d6de09d3fc865aceaafd9b3617`; root review SHA256 `da753d98c65882ea3ee0eb9619525964693f60066b18634af5e6ce682d742427`.

Source144 is the first ordinary run under the tested V4 orchestration and qualified transport snapshot. The segmentation policy, prompts and geometry remain V30; the changed Client recognizes the successful source61 transient recovery cache. V4 passed 22 VM guard checks plus independent static review and actual accepted61 qualification before root dispatch. It uses the same $20/480-request suite, original per-case limits and $100 global cap. Old terminal outputs remain closed.

Source56 and100 both passed root inspection of the source and every exact crop. Source56 accepted eight panels at Sol-low in8.986seconds, with16new native checks/$0.003560 and one cached response. Source100 accepted five at Sol-low in6.209seconds, with10new native checks/$0.002536 and one cached response. These cache-assisted validation costs exclude the previously paid detectors. All26new reservations settled. Global used/held after100 is$49.762165; suite243requests/$6.910833. Root review hashes are `d19224becac91c4f988e62fdc2bef18c3486786d618019b08975706518a0431d` and `8932b301d1ddcd6b0ce28817e3e9d672e95d270ae63db636e4f601ef9f8b3052` respectively.

Page144 browser playback passed all three inspected screenshots with exact source/geometry binding and zero exceptions. Its17-file verified export is1049070bytes, SHA256 `5e24771e18f9d3757067ebd9098dafd000b3e03782424cfbd27f6c64b6ae6312`; visual receipt `59a8c4f6f73d5716aafb7490ab5f7caa73796b1401e423ee7a945ae7a63fd834`. The phone catalog remains unchanged.

Page56 and100 browser playback passed overview, every panel and end, with all9/6screenshots personally inspected and zero exceptions. Their exact source and panel geometry match the original automatic outputs. The respective verified browser exports are3057130bytes/23files, SHA256 `be2c3118b9b1233606b66f05c95cce5eef67ad692537a51a67991bedd6fda963`, and2081983bytes/20files, SHA256 `eb255a55a654e19e3c8f0288099e814796d6768c4e8880ec816591e358c4d9b3`. No phone catalog or stable installation change.

Source205 exposed a scheduling bug rather than a provider/quota error: native worker selection read global headroom while the nested $4 page guard had only $2.713011 available. The guard stopped the third concurrent reservation before overspend. All47 successful requests settled to$1.286989; no unknown request is retried. At that historical stop source205 was unaccepted; its original terminal remains preserved. Global used/held at this stop is$51.049154; suite290/$8.197822. A separately tested continuation must expose nested headroom to the unchanged worker calculation, reuse all exact successful responses, and count both runs under the original dollar ceilings. Root prospectively allocated160 cumulative requests for205; the suite ceiling remains480.

Root's source/all10-crop review of the last Astra proposal is diagnostic only, with receipt `b1c4926724756ac023843aee8c0a6c9bad0a94f08e176684aeeceb70c2593597`. The earlier [Sol-high ground rejection](source205-v30-rejection-audit-20261009.md) has ambiguous exclusive ownership; it is neither confirmed subject loss nor a confirmed false alarm. This does not authorize accepting a proposal with incomplete automatic checks.

Source205 continuation subsequently accepted all10panels automatically. Its16new
requests settled to$0.304194, with49cachehits in136.647s. All source/crop hashes
match the exact root-reviewed diagnostic images, now bound by accepted receipt
`9d4f93ed3af736e84602aff4837a50246295499923d2e80f6d5e6189887b6989`.
No model repair or human routing was applied. Nested-headroom scheduling changes
only the available budget exposed to unchanged worker selection; quality source
and prompts are unchanged. Original+continuation205 cost is$1.591183/63requests;
globalusedheld$51.353348, same suite306/$8.502016. Browser playback is pending.
Accepted CBZ SHA256 `ed018c263910d975c0092addd25875a57ee5c8bbdbe5d16c16458194613d5664`.

Source205 actual reader playback subsequently passed overview+10/end with all11
screenshots inspected and0exceptions, exact source/geometry and unchanged archive.
Browser export `reader-v30-source205-20261009/actual-v30-source205-browser-evidence.tgz`
is4307991bytes/26fully read regular files, SHA256
`5dce017249b536873797363e0f9c90c56801422bdad762fd661909578d485de1`;
visual receipt `da1abe8d50a5f2c6034261e0a8b93665d9263da31a53cd5c6eda97c035289d66`.
The reader registry is51; separate browser-worker17/Orca32. All nine individual
development cases now pass root crop review and actual browser playback. The
six-page prefix is running one page at a time; first four whole-page front-matter
pages passed root review with no new requests (two exact cache hits each).

The six-page prefix subsequently completed and passed root review at every
one-page checkpoint. Counts are `[0,0,0,0,7,7]`: four whole-page front-matter pages
and two seven-panel narrative pages. Both narrative pages automatically escalated
Sol-low→Sol-high with source-ownership and scoped crop checks; no human geometry
or routing entered the run. Page5 added21requests/$0.407946; page6 added20requests/
$0.513481. Combined prefix41requests/$0.921427,14cachehits across six invocations;
all new reservations settled. Globalusedheld$52.274775, suite347/$9.423443.
The final completed summary's20newcalls/260.862s refer only to the last invocation,
not the whole prefix or a cold run. The page6 ownership audit alone took204.2s.
Root receipts bind every actual source/crop; page6receipt
`72a76f6e2eaafdff04d8e87f67af0b12ef92d4b2c249c82b2f3dce9fcd7d5696`.
Actual CBZ SHA256 `f5fc162a43f88b755aa246d91eb24fa7d334c8328a4e87dee4a2ee9b2595a37b`.
Four-format cache-only parity and actual browser playback are next. The frozen
independent screen and full257 remain unrun.

The unchanged four-format harness completed six accepted pages for each of
PDF/CBZ/genuine compressed CBR/folder, with55exactcachehits/0newrequests perrun.
It reports full geometry/source/ACBF/profile/escalation parity, unchanged source
and ledgers, and counts[0,0,0,0,7,7]. Actualall-step browser validation is running
separately. The standaloneprefix quiescent export17100333bytes/340fullyreadfiles
hasSHA256 `689f5bc196d4c6b7180d290b57f5873ac2591dda29ced28ae41eb3af7f15259c`;
all7172ledgerrowsparse, ledger `d9066dd2b7fa77138266b669174e8f355a64886f5f7bae4b94eb22695a13831e`.
Root verified all41prefixreservations settled exactlyonce, zero unknownprefixholds.

All four actual archives subsequently passed browser playback:80/80metadata steps,
four end boundaries,0exceptions, exactgeometry/source bindings andvalidACBF/profile
LTR. Browserreview covered31distinctscreenshotbytevariants;49othercaptures matched
those inspected bytes. Stable reader/code/catalogunchanged. This closes panelized
format integration for these outputs, separately from the failed N1 qualitycontrol.
Converterexport668files SHA256 `cfebbb79c80d6a9ddae205577b445aafb975070006253bc6c9df7b16cbeac359`;
browserexport142files SHA256 `d4bb927eb10af5a09433b37953be1791132203aef6198f2bb959a755cea356da`.
