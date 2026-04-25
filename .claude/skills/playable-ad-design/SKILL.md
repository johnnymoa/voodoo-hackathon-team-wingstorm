---
name: playable-ad-design
description: Authoritative playbook for designing high-performing mobile playable ads — the principles, hooks, beat structure, technical constraints, juice, audio, palette, CTA, variation strategy, and what to measure. Use when building, judging, or iterating on a playable HTML ad — when the user says "make this playable better", "what makes a good playable", "review this playable", "help me think about the gameplay loop", "design a playable for X", or when proposing a new playable variant or activity edit. Pairs with playable-forge (runs the workflow), inline-html-assets (final pack), and iterate (tunes via feedback). Always consult before deciding what to change in a playable's CONFIG, mechanic, or art direction.
---

# THE CASUAL GAME PLAYABLE AD PLAYBOOK

What actually makes a high-performing playable, with receipts.

A "playable ad" is a 10–60 second interactive HTML5 mini-experience that runs
inside an ad slot (AppLovin, Mintegral, Vungle, IronSource, Meta Audience
Network, TikTok). It is the highest-converting format in mobile UA today
(IPM 2–4× video on average for casual games) — but the format is unforgiving:
you have ~3 seconds to earn the next 7, and the file must be a single
self-contained HTML under ~5 MB with no external network calls. Everything
below is engineered around those constraints.

---

## 0. The first principle

A playable is not a demo of your game. It is a *promise* of a feeling, made
testable in 30 seconds. The player must finish the playable thinking "I get
it, I want more of that," not "I just played the game."

Corollary: the playable's job is install intent, not retention. Optimize for
the screenshot in the player's head 4 seconds in.

---

## 1. The 3-second rule (the hook)

Mobile ad attention dies at ~3s. The first frame must answer three questions
without text:

- What am I looking at? (subject readable at thumbnail size)
- What can I do? (one clear interactive affordance)
- Why should I care? (tension, curiosity, or anticipation)

Hook archetypes that consistently win in casual (these align with the
`LABEL_VOCAB` your own pattern extractor ranks against — they aren't
theoretical):

- **near-fail tease** — character is one inch from disaster; player must
  intervene. Used by: Subway Surfers, Hill Climb Racing.
- **fake-fail / wrong choice** — show a stupid solution failing first, then
  invite the player to do it right. Used by: Royal Match ("Help the King!"),
  Hero Wars (pull-pin), Gardenscapes (the canonical bait-and-switch).
- **satisfying-completion** — the visual *almost* completes itself; the
  player just nudges. Used by: Water Sort, Color Sort, Wood Block puzzles.
- **puzzle-with-bad-solution** — present a tile/board where the obvious
  move obviously breaks. Used by: Match Masters, Toon Blast.
- **before-after-transformation** — split-screen ugly-vs-pretty,
  dirty-vs-clean, sad-vs-happy. Used by: Project Makeover, Manor Matters.
- **pull-to-aim** — finger appears, drags, releases; physics resolves.
  Used by: Angry Birds, Knock 'em All.
- **rage-bait** — deliberately stupid AI character that the player wants to
  "fix." Used by: Save the Doge, Save the Girl.
- **asmr / sensory** — soap cutting, slime stretching, paint mixing. Sound
  off by default, so it must work mute. Used by: ASMR Slicing, Make Slime.
- **narrative-reveal** — micro-story (5s mini-cutscene) framing the goal.
  Used by: Lily's Garden, Family Hotel.
- **humor-fail** — character does something absurd and the player corrects.
  Used by: Stupid Zombies, High Heels.

Pick ONE hook. Layered hooks dilute. The pattern extractor is right to
force a single label per creative.

---

## 2. The opening visual

What the camera does in frame 1 is as decisive as the hook. Effective
options:

- **ui-isolated** — strip everything but the one element the player will
  touch. Works for puzzles where the board IS the message.
- **hero-character-closeup** — face fills the frame; emotion does the
  talking. Works in narrative casual (Project Makeover, Choices).
- **level-overview** — top-down or 3/4 of the whole board, so player sees
  the whole problem space. Works in match-3, merge, board games.
- **extreme-zoom** — exaggerates a single mechanic (a single coin merging
  into another). Used in idle/merge ads.
- **split-screen** — two outcomes side-by-side. The "you vs them" or
  "before vs after" hook.
- **text-overlay-question** — "Can you solve this?" "99% fail this!" Use
  sparingly; algorithm-flagged on some networks.
- **fail-state-first** — open with the player losing, then rewind.
  Curiosity spike, but burns trust if overused.

Rule of thumb: at thumbnail resolution (a 240 px tall preview) every shape
in frame 1 must still be identifiable. If it's mush at 240 px, it's mush
in the feed.

---

## 3. The core mechanic slice

You are NOT shipping the game. You are shipping a *30-second representative
slice* of one mechanic. The choice of mechanic, in casual:

> match-3, merge, physics-drop, pull-pin, tower-defense, runner, shoot-aim,
> stack, color-sort, rope-cut, draw-path, tap-rhythm, build-place,
> conquer-territory.

Selection criteria — in priority order:

1. **One-input** (tap, drag, or hold). Two inputs = installs lost.
2. **Self-evident.** Player should figure it out without a tutorial in <2s.
3. **Loopable.** The mechanic must produce repeatable wins inside 30s.
4. **Photogenic.** The "wow moment" must read at thumbnail scale.
5. **Honest enough.** If your real game doesn't have this mechanic at all
   (the Gardenscapes / Hero Wars problem), you will get high IPM and
   terrible D7 retention. Most networks now penalize this. Best
   compromise: derive the mechanic from a real subsystem.

The `playable_template.html` in this repo encodes this discipline — one
canvas, one mechanic loop (`spawn → tap → resolve`), one win condition,
one fail condition, one CTA.

---

## 4. Structure — the 0–30 second beat map

This is the structure `briefing.py` writes into every brief, and the
structure that wins:

```
0–2s    HOOK.   Most compelling visual. Pose the question.
                (No CTA yet. No instructions yet.)
2–6s    TEASE.  Fail or near-fail. Bait curiosity. First input prompt.
                (Hand pointer / pulsing target appears at ~1.5s if no input.)
6–18s   PLAY.   Player produces 2–4 small wins. Difficulty ramps ~1.05× per win.
                Score / progress bar fills. Juice escalates.
18–25s  PAY-OFF. The "big" win. Screen shake, particle burst, sound.
25–30s  CTA.    Pulsing install button. Auto-show after either:
                - score ≥ N (e.g. CONFIG.showCtaAfterScore: 6), or
                - Ms elapsed (e.g. CONFIG.showCtaAfterMs: 12000), whichever first.
30s+    LOOP.   Auto-restart silently if no install tap. Don't punish
                the lurker who watched but didn't tap — give them another chance.
```

Test: if you mute the playable and play it for 5 seconds, can you describe
what happens next? If yes, the beat map is working.

---

## 5. Controls & input

- **Touch-first.** No hover states. No keyboard. No right-click.
- **Big targets.** Minimum 44×44 CSS px (Apple HIG). Use a `tapRadius`
  config like the template's `CONFIG.tapRadius: 56` so taps are forgiving.
- **One-finger.** Multi-touch is great for retention, terrible for ad
  install.
- **No drag-to-scroll.** Lock the viewport, set `touch-action: manipulation`,
  `overflow: hidden`, `user-select: none`. The template does all of these.
- **First-tap-anywhere starts the game.** Don't make players hunt the start
  button — the entire screen is "tap to play."

If a player hasn't tapped by ~1.5s, surface a hint — either a pulsing
finger, an arrow, or a "Tap!" overlay. The template uses
`showHintAfterMs`.

---

## 6. Juice (why players tap twice)

"Juice" is the layer of effects that turn an interaction into a feeling.
Casual playables that perform have all of:

- **Squash & stretch** on tap (scale 1 → 1.15 → 1 over 120ms).
- **Particle burst** on success (8–16 particles, lifetime 400ms, fades).
- **Color flash** on win (full-screen overlay, 80ms, low alpha).
- **Screen shake** on big events (8–12 px amplitude, decay over 200ms).
- **Score count-up** (don't snap to new value; ease over 300ms).
- **Number pop-ups** on score (+1, +5) drifting upward, fading out.
- **Combo / streak indicators** if applicable.
- **Easing curves everywhere** — cubic-out, back-out. Linear motion is
  dead.

What to skip in the playable specifically:

- Loading screens (cold start should be <1s after asset decode).
- Tutorials with text. Use diegetic hints (pulsing target, animated
  finger).
- Achievements / badges / collection screens. Wrong dopamine for a 30s
  window.

---

## 7. Audio

- **Default to MUTE.** ~80% of mobile ad impressions are sound-off.
- **Visual must work without audio.** Period.
- IF audio plays, it should reinforce taps (low-pitched UI clicks,
  satisfying chimes on success, restrained whoosh on transitions).
- **Music**: optional, low volume, no lyrics, loop seamlessly. Many
  networks auto-mute opening seconds — design around it.
- Use Web Audio API or inline base64 OGG/MP3. No `<audio src="...">`.
- **Total audio budget: ≤ 200 KB.** Most playables ship 1 success chime,
  1 fail buzz, 1 ambient loop, that's it.

---

## 8. Palette & art direction

Top-performing palette moods on TikTok / Meta for casual (again from
`LABEL_VOCAB` ranking):

- **saturated-cartoon** — high chroma, soft outlines. Royal Match,
  Toon Blast.
- **neon-pop** — cyan/magenta/lime against near-black. Hyper-casual
  standby.
- **high-contrast** — primaries on white or black. Match Masters, Wood
  Block.
- **warm-cozy** — peach, cream, terracotta. Lifestyle / interior-design
  casual.
- **muted-realistic** — semi-realism. Tower defense, war casual.
- **dark-fantasy** — desaturated jewel tones. Mid-core leaking into
  casual.

Constraints to follow:

- Max ~6 hues in the active palette. The template default is 5.
- Hero color (CTA, win indicator) should not appear elsewhere.
- Test in grayscale. If hero/enemy aren't distinguishable in grayscale,
  you've failed colorblind users (~8% of male audience).
- Sky-floor contrast: top 30% of frame must contrast with bottom 30%.

---

## 9. The call to action

CTA framings that consistently outperform "Download Now":

- **imperative-verb** — "Save the King!" "Build your village!" "Match 3!"
  Highest CTR in casual. Implies the install IS the action.
- **question** — "Can you solve it?" "Think you're smart?"
- **challenge** — "99% fail this. Can you?" Network-flagged if hyperbolic.
- **social-proof** — "Join 50M players" — works in mid-core, weaker in
  casual.
- **urgency** — "Ends today" — banned on most networks for non-time-limited
  products.
- **free-prize** — "Free skin inside" — works only if the game actually
  has it.
- **you-can't-do-this** — reverse-psychology dare. Surprisingly effective.

CTA design rules:

- Single button. No "Maybe later" / "Skip" — leave the network to handle
  it.
- Pulsing or breathing animation (1.0 → 1.05 → 1.0 over 1.2s).
- Bright accent color reserved for the CTA only.
- Bottom-center placement, with safe-area inset for iPhone notch.
- Tappable area should be 1.5× the visible button size.
- Show CTA earlier on win, later on near-loss — match emotional context.
- The full canvas should be a fallback CTA after 30s if user hasn't
  tapped.

---

## 10. Technical constraints (HARD RULES)

These are not preferences. Networks will reject builds that violate them:

- **SINGLE FILE.** One `.html`. No external scripts, fonts, images, or
  audio. Everything inlined as base64 / data URLs. (See the
  `inline-html-assets` skill.)
- **SIZE BUDGET.** ≤ 5 MB total. Many networks: ≤ 3 MB. AppLovin: 5 MB
  hard cap. The closer you are to the cap, the slower the cold start.
- **NO NETWORK CALLS at runtime.** No `fetch()`, no XHR, no analytics
  ping. The container provides install reporting via mraid /
  FbPlayableAd / ExitApi. The template's `Net` shim handles all four
  with try/catch no-ops — that's the correct pattern.
- **MRAID 2.0+ COMPLIANT.** Listen for `ready`, `viewableChange`. Pause
  render when off-screen. Fire `mraid.open(storeUrl)` on CTA tap.
- **VIEWPORT META.** Vertical 9:16 primary. Horizontal supported but not
  required. Use `viewport-fit=cover` for safe-area on notched devices.
- **COLD START < 1s** after HTML decode. Lazy-decode any base64 image
  > 100 KB using `Image.decode()` to avoid jank.
- **NO 3rd PARTY FRAMEWORKS** over a few KB. React/Vue/Three.js are dead
  on arrival in a 5 MB budget once you add assets. Vanilla canvas + a
  tiny helper (~5 KB) is the norm. The template uses raw
  `getContext("2d")`.
- **DPR-AWARE RENDERING.** Cap at 2.0 (template does this). Higher DPR
  = pointless GPU cost on phones.
- **TOUCH-ACTION: MANIPULATION.** Disables 350ms tap delay on iOS Safari.
- **NO ALERTS, PROMPTS, CONFIRMS.** They block render and break MRAID
  state.
- **NO COOKIES, LOCALSTORAGE, INDEXEDDB.** Not allowed in most ad
  sandboxes.
- **NO COPYRIGHTED ASSETS,** no real people, no logos you don't own.
  Generated or licensed only.
- **TYPE ≥ 24 px equivalent.** Anything smaller is unreadable on mobile.

---

## 11. Variation strategy (why CONFIG matters)

A playable shipped without variants is a rounding error. Production
playables ship 4–12 variants from day one because you cannot predict the
winner — the network will A/B them and stop spending on the loser within
hours.

How to vary effectively (in descending impact order):

1. **HOOK / OPENING.** Same mechanic, different first 3 seconds. Largest
   IPM swing — often 2–3×.
2. **CTA TEXT & TIMING.** "Install Now" vs "Save the King!" vs "Help me!"
   Plus timing: show after score 3 vs score 6 vs 15s.
3. **PALETTE.** Same scene, swap the 5–6 hues. Surprisingly large effect
   on thumbnail click-through.
4. **DIFFICULTY.** `enemySpeed`, `spawnEverySeconds`, `winScore`. Easier
   wins more on cold audiences; harder on warm.
5. **CHARACTER / THEME SKIN.** Knight vs Wizard vs Robot — only matters
   if your app icon / store page uses the same character.
6. **WIN/FAIL FRAMING.** Auto-win after 5s (very high IPM, very low D1
   ret), vs honest play (lower IPM, higher D1 ret).

The `CONFIG` block at the top of every playable in this repo is what
makes this scalable: every variant is a 30-second JSON edit, and
`generate_variations` just rewrites that block.

Anti-pattern: producing 12 variants that differ only in cosmetic details.
Pick variants that test *hypotheses about what the audience wants*, not
*possible knob settings*. The pattern to follow: feed `creative_forge`'s
`patterns.json` into `playable_forge` so each variant tests a specific
ranked market signal, not a random parameter sweep. (When you build that
composed pipeline via `/new-pipeline`, that's the design.)

---

## 12. Case studies — what actually shipped and won

**ROYAL MATCH (Dream Games)**
Hook: "Save the King!" pull-pin / wrong-choice (the king will boil unless
you remove the right pin). Real game: match-3. The pull-pin playable was
so successful it became a brand asset; Dream Games eventually added the
pull-pin mechanic into the core game to fix the bait-and-switch.
*Lesson: if your playable hook outperforms your real loop, change the
real loop.*

**GARDENSCAPES (Playrix)**
The original bait-and-switch case. Pull-pin / save-the-character ads
drove top-grossing UA for years while the real game was match-3. Caused
industry-wide network rules tightening on creative-product mismatch.

**PROJECT MAKEOVER (Magic Tavern)**
Before/after split-screen hook + dressing-room mini-game. Player picks
"ugly" or "pretty" outfit; if they pick ugly, scene visibly judges them.
Pure rage-bait engagement. Real game has the dress-up mechanic, so it
passes the honesty test.

**SUBWAY SURFERS (SYBO)**
Near-fail playable: train-rapidly-approaches scenario. One swipe to
dodge. Auto-win bias at first attempt. Among the longest-running playable
ads in mobile history (>5 years in rotation, minor variants).

**WATER SORT PUZZLE**
Pure satisfying-completion. The board IS the ad. Two-tap to pour water
between tubes until colors separate. ~95% completion rate inside 15s,
which is why it floods every network.

**SAVE THE DOGE**
Rage-bait + draw-path. Player draws a line to block water/lava from a
helpless cartoon dog. Maximally weaponized "you must intervene" trigger.

**CUP HEROES** (the example in this repo)
Squad-merge tower defense. Hook is the auto-battler clearing waves while
player merges cups. Player taps to upgrade. Strong "watch number go up"
and "satisfying-completion" overlap.

Pattern across all of them: ONE mechanic, instant comprehension, wins
within first 10s, escalating juice, single CTA.

---

## 13. What to measure (post-launch)

The four numbers that matter, in order:

1. **IPM** (Installs Per Mille impressions). The headline. >10 is good
   for casual, >20 is excellent, >40 is rare and probably bait.
2. **CTR** (engagement rate / tap rate). Tells you if the hook works.
3. **Completion rate** (% who reach the CTA naturally). Tells you if
   the loop works. Below 40% means your difficulty curve or session
   length is off.
4. **D1 / D7 retention** of installs from this creative. Tells you if
   the playable is honest. If IPM is high but D1 < 20%, you're baiting.

Networks now weight a "creative quality score" that combines these.
A high-IPM / low-D7 playable will be quietly throttled within a week.

---

## 14. The quick checklist (print this)

- [ ] Single `.html` file, no external assets, ≤ 5 MB
- [ ] Vertical 9:16 default, viewport meta with safe-area inset
- [ ] Touch-only, single-finger, taps ≥ 44 px, tap-anywhere-to-start
- [ ] First frame readable at thumbnail size, in grayscale, muted
- [ ] Hook lands in 0–2 seconds, hint appears by 1.5s
- [ ] One mechanic, one input, one win condition, one fail condition
- [ ] First win by ~6 seconds, big payoff by ~20 seconds
- [ ] Juice on every meaningful event (squash, particle, shake, sound)
- [ ] CTA pulses, single accent color, bottom-center, safe area
- [ ] Auto-loop after 30s if no install tap
- [ ] mraid / FbPlayableAd / ExitApi shims present, all in try/catch
- [ ] CONFIG block at top of file for 30-second variant edits
- [ ] At least 4 variants ready, each testing a different hook/CTA/palette
- [ ] Tested on AppLovin Playable Preview AND a real iPhone AND a real Android
- [ ] Real game contains the mechanic shown (or close enough to defend)

---

## 15. Further reading / tools

- AppLovin Playable Preview — <https://p.applov.in/playablePreview?create=1>
- Sensor Tower Creative Library — top-performing ads by genre/network
- IAB MRAID 3.0 spec — <https://www.iab.com/guidelines/mraid/>
- Facebook Audience Network Playable spec
- Voodoo / Homa / Lion Studios public publisher docs
- "Universe of Ads" YouTube channels (Matej Lancaric, Two & a Half Gamers)
  for ongoing pattern teardowns
