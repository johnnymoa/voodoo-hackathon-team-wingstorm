---
name: video-ad-design
description: Authoritative playbook for designing high-performing mobile video ad creatives — the hook structure, beat map, pacing, tone of voice, sound design, on-screen text, end-card composition, variation strategy, production tiers, and what to measure. Use when building, judging, or iterating on a video ad — when the user says "review this brief", "make a stronger video ad concept", "what's the right hook", "help me think about the storyboard", "design a TikTok ad for X", or when proposing a new creative_forge config, brief, or Scenario prompt. Pairs with creative-forge (runs the brief pipeline) and scenario-generate (renders the asset). Always consult before changing a brief, prompt template, or pattern-extraction approach.
---

# THE CASUAL GAME VIDEO AD PLAYBOOK

What actually makes a high-performing non-interactive marketing video,
with receipts.

A "video ad" here means any non-interactive moving creative shipped to
TikTok, Meta (Facebook/Instagram Reels & Stories), YouTube (Shorts and
in-stream), Snapchat, Apple Search Ads (custom product pages with video),
AppLovin / Mintegral / Vungle / IronSource video slots, or organic
TikTok/Reels brand channels. Lengths range from 6-second bumpers to
2-minute "episode" ads. The format is structurally different from a
playable — you cannot rely on the player's hand to carry attention, so
every second has to earn the next.

---

## 0. The first principle

A video ad is an emotional vignette that ends in a logo. The viewer must
feel something specific (curiosity, satisfaction, vindication,
schadenfreude, nostalgia, FOMO) before the brand name appears. If the
viewer remembers the feeling but not the brand, you wasted spend; if they
remember the brand but felt nothing, they will not install. The job is
both, in that order.

Corollary: the first frame is more important than the last. The last
frame only happens for people you've already won.

---

## 1. Format, duration, aspect ratio

Optimal lengths by placement (current as of 2026):

```
TikTok In-Feed              9–34s sweet spot, 21–34s wins UA right now
TikTok Spark / Creator      30–60s, longer if narrative justifies it
Instagram Reels / FB Reels  9–15s for top-funnel, 30s for performance
Instagram / FB Stories      ≤ 15s (auto-skip after)
YouTube Shorts              15–45s, 30s is the median high-performer
YouTube In-Stream skippable 30s primary, 6s bumper for retargeting
Snapchat                    ≤ 10s for top-funnel, 15–20s for conversion
AppLovin / Mintegral video  15s or 30s, autoplays muted-then-unmute
Apple Search Ads CPP video  15–30s vertical, no audio reliance allowed
```

Aspect ratios — produce these three masters from one shoot:

- **9:16 vertical** (1080×1920) — primary for everything mobile-feed
- **1:1 square** (1080×1080) — Meta feed fallback, defensive
- **16:9 horizontal** (1920×1080) — YouTube in-stream + cross-channel

Safe zones (do not put text/CTA outside these on 9:16):

- Top 250 px reserved (handle, "Sponsored", network UI)
- Bottom 450 px reserved on TikTok (caption, music tag, sidebar)
- Right 200 px reserved on TikTok / Reels (sidebar)
- Center 1080 × 1200 is the "always visible" zone — put hero action here

Frame rate: 30 fps default. 60 fps for hyper-casual where motion
smoothness is part of the appeal. Never above 60 — most networks
transcode it down.

Bitrate / file size: aim 8–12 Mbps for 1080p H.264. Most networks cap at
~500 MB upload; useful target is 50–80 MB for 30s, which keeps the
upload fast enough for 30+ variant launches in one session.

---

## 2. The 1.7-second rule (the hook)

Meta's own internal data: 47% of video ad value is delivered in the first
3 seconds. TikTok's threshold is even shorter — measurable drop-off
begins at 1.7s. You have, effectively, two seconds to win.

Hook archetypes that consistently deliver in casual video (these overlap
with the playable `LABEL_VOCAB` but with video-specific siblings):

**Pattern-interrupt hooks — break the scroll**

- **visual-anomaly** — wrong color, wrong scale, wrong physics. "Why is
  that cat the size of a building?" Used by: Mob Control, Stumble Guys.
- **near-fail / cliffhanger** — character is mid-disaster. "Will they
  make it?" Used by: Subway Surfers, Hill Climb Racing, Last War:
  Survival.
- **POV / first-person** — "you" are the protagonist. Phone screen
  recording style, hand reaches in. Used by: Royal Match, Last War.
- **text-overlay-question** — "Could you beat this?" "99% give up here."
  Used by: Royal Match, Project Makeover, every IQ-test ad ever made.
- **celebrity-cameo** — known face in frame 1. Used by: Coin Master
  (J.Lo, Cardi B, Ryan Reynolds), Raid Shadow Legends (every YouTuber
  alive).
- **mock-UGC opener** — "Wait, you guys haven't downloaded X yet?"
  delivered direct-to-camera by a creator-style talent. Used by: Stumble
  Guys, Marvel Snap, Squad Busters.
- **before-after** — split-screen ugly-vs-pretty, broken-vs-fixed. Used
  by: Project Makeover, Manor Matters, Township.

**Emotional hooks — induce a specific feeling fast**

- **rage-bait** — character makes a wrong choice; viewer wants to scream.
  Used by: Save the Doge, High Heels, Gardenscapes ads.
- **satisfying-completion** — visual nearly resolves itself; ASMR
  territory. Used by: Water Sort, Color Sort, ASMR puzzle ads.
- **narrative-cliffhanger** — open with consequence, rewind to setup.
  Used by: Last War: Survival ("How did I end up here?"), Whiteout
  Survival.
- **humor-fail** — character does something stupid; viewer laughs. Used
  by: Stumble Guys, Fall Guys clones, Stupid Zombies.
- **status-fantasy** — protagonist visibly winning at life because of the
  game. Used by: Coin Master ("look at my village"), Hero Wars.

Pick ONE hook. A muddled hook is worse than a weak one — the algorithm
needs a clear watch-time signal to decide whether to spend more.

---

## 3. The first frame — composition rules

Treat frame 1 as a print ad that has 0.5 seconds to communicate. Rules:

- **One subject.** The hero element fills 30–60% of the frame.
- **Face if available.** Faces (especially eyes) double stop-rate vs
  object-only opens.
- **Eye-line contact OR motion.** If a face, look toward camera. If no
  face, something must be visibly moving (animation loop, particle).
- **Text on frame 1 is allowed,** but ≤ 5 words and ≥ 64 px equivalent.
- **Avoid logos in frame 1.** Logo = ad signal = thumb-down reflex.
- **High contrast** — pass the "squint test." If you squint at the frame
  and can't tell foreground from background, recompose.
- **Saturation up.** Casual ad feeds are saturation-arms-races; muted
  opens lose unless the genre IS muted (e.g. survival, dark fantasy).
- **Rule of thirds** for the hero element; dead-center for symmetric
  hooks.
- **No black or letterbox bars** on frame 1 — the algorithm treats them
  as low-quality signal.
- **No on-screen UI controls** (avoid looking like a screen recording
  UNLESS that's the deliberate "mock UGC" style).

Anti-patterns observed losing in 2026:

- Logo-on-blank-color cold open (1990s TV ad muscle memory).
- Slow zoom from black. Algorithms penalize "no information in frame 1."
- Split-second studio bumper (logo flash). Counts as the entire hook
  for most viewers.

---

## 4. The storyboard — full 30-second beat map

This is the structure that wins for casual game video ads. Times are
guidelines; tighten or loosen by ±20% depending on length.

```
0:00–0:02  HOOK FRAME
           Pattern-interrupt visual. Subject established. Question
           implicitly posed. ZERO branding. NO logo. NO CTA.
           Sound: optional sting (low-pitched, ≤ 200ms) or silence.
           Subtitle: optional 1–5 word teaser ("Wait for it…").

0:02–0:05  SETUP / TENSION
           Introduce the stakes. Show what's at risk or what's wanted.
           Cut rate: 1 cut per 1.0–1.5s. Camera moves in (push-in or
           whip-pan). First on-screen text appears here if any.

0:05–0:10  THE "MOMENT"
           The single most photogenic 5-second window. Often:
           - first big satisfying win (puzzle resolves)
           - first big fail (character wipes out)
           - first big reveal (character transforms / village upgrades)
           Cut rate accelerates: 1 cut per 0.6–0.8s. Particle / juice
           escalates. Music drops or builds.

0:10–0:20  PROOF / VARIETY MONTAGE
           Quick cuts showing OTHER things the game does. 4–8 micro-clips
           (~1.0–1.5s each). The viewer needs to think "this isn't a
           one-trick game." Music carries the cuts.
           Insert: "300M+ players" or social proof title card if you
           have one (≤ 1s, mid-frame, large type).

0:20–0:25  EMOTIONAL PEAK
           Biggest reveal: huge battle, ultimate skin, completed village,
           leaderboard win, transformation reveal. Sound peaks. Slowest
           shot of the entire ad goes here (1.5–2s) — let the moment
           land. This is the screenshot the viewer will remember.

0:25–0:28  CTA SETUP
           Logo appears. Tagline appears. Hero character does a final
           beat (waves, nods, points at logo). Music resolves.

0:28–0:30  END CARD / CTA
           Hard stop on a clean composition: logo + tagline + store
           badges + "Play Free Now" / "Download Now". Hold for 2s. NO
           motion (or very slow loop). This is what the viewer will see
           paused. Make it screenshot-worthy.
```

For 15-second ads compress: hook 0–2s, moment 2–8s, montage 8–11s, peak
11–13s, CTA 13–15s.

For 60-second ads (creator-style or narrative episodes): hook 0–3s,
act 1 setup 3–15s, act 2 escalation 15–35s, act 3 payoff 35–50s, CTA
50–60s.

---

## 5. Pacing & editing

Average shot length (ASL) targets by genre:

```
Hyper-casual          0.6–1.0s ASL — almost music-video pacing
Casual puzzle         0.8–1.2s ASL
Casual narrative      1.2–2.0s ASL with slow beats for emotional reveals
Mid-core / strategy   1.5–2.5s ASL with cinematic holds
Hyper-narrative       2.0–4.0s ASL (Last War style)
```

The "attention curve" — the rough percentage of viewers still watching
at each second on TikTok / Reels for a well-performing 30s casual ad:

```
0s   100%
3s    65%   (the cliff — pass this and you have a chance)
10s   45%
15s   38%
20s   33%
30s   28%   (3-second view rate baseline; install rate rides on this)
```

Implications:

- **Front-load what matters.** The hook and the moment must both fit
  inside the first 10s, because half your audience leaves there.
- **Loop awareness.** On TikTok / Reels, ads autoplay-loop. Design the
  last frame to flow visually back into the first. If the loop creates
  a seamless moment, your watch-time metric doubles.
- **Cuts on beat.** If you have music, every cut should fall on a beat
  (either downbeat or 1/8 subdivision). Off-beat cuts feel amateur and
  the algorithm correlates "amateur" with "skip."
- **Motion blur and whip-pans bridge cuts.** Cheap, effective, hides
  budget constraints.
- **Match-cuts** (one shape resolves into another) are the single most
  rewatchable edit type. Use one if you can.

---

## 6. Tone of voice

The seven tones that work for casual game video, with examples:

1. **EARNEST HYPE (broadcast announcer)**
   "Welcome to Royal Match. Help the King! Solve puzzles!"
   Loud, confident, slightly cheesy. Works for puzzle, match-3, idle.
   Used by: Royal Match, Toon Blast, Coin Master.

2. **CASUAL CREATOR / MOCK UGC (TikTok-native)**
   "okay so I just downloaded this game and I'm OBSESSED."
   Direct-to-camera, handheld, no broadcast polish. Works for any genre
   targeting <30 audience. Used by: Stumble Guys, Marvel Snap, Squad
   Busters, Last War's "I tried this game so you don't have to" angle.

3. **DEADPAN / IRONIC**
   "I am 34 years old and I play this puzzle game. There is no excuse."
   Self-aware, low-affect. Counterintuitively high CTR with millennial
   audience. Used by: Royal Match's late-2024 ironic pivots, several
   Voodoo titles.

4. **NARRATIVE / CINEMATIC VO**
   "When the world ended, only one thing mattered: survival."
   Movie-trailer cadence. Works for survival, strategy, cinematic
   casual. Used by: Last War: Survival, Whiteout Survival, Clash of
   Clans cinematics, Raid Shadow Legends.

5. **CHARACTER VOICE (in-world)**
   Character speaks as themselves, breaking the fourth wall. Used by:
   Brawl Stars character spotlights, Clash Royale's King-narrator ads,
   AFK Arena hero spotlights.

6. **NO VOICE / MUSIC-ONLY**
   Visual carries everything; music sets the mood. Highest portability
   across markets (no localization), strongest on TikTok where ~80% of
   viewers watch muted anyway. Used by: Most hyper-casual, Water Sort,
   Wood Block, ASMR ads.

7. **CHALLENGE / DARE**
   "Bet you can't get past level 5."
   Aggressive, confrontational. Spikes engagement, can damage brand if
   overused. Used by: Hero Wars, Lily's Garden, IQ-test puzzle ads.

Rules across all tones:

- Pick ONE per ad. Tonal whiplash kills retention.
- Match the tone to the audience persona, not the game's content. A
  cozy farming game can ship in ironic-deadpan if the audience is
  gen-Z.
- Localize voice talent, not just translate copy. A US-cast VO read in
  French sounds like a 1990s Hollywood movie dub.

---

## 7. Sound design & music

The single most ignored axis. Most teams use library music as filler;
high-performers treat sound as a primary creative axis.

Music selection priorities (in order):

1. Fits the tone (see above).
2. Has a clear rhythmic structure for cut-syncing.
3. Builds — has a perceptible energy arc, not just a loop.
4. Has a hook of its own — the music itself should be slightly
   addictive.
5. License-clean for paid usage, all geos, all networks.
6. Costs nothing or close to it.

Where to source:

- Epidemic Sound, Artlist, Musicbed (subscription, broadest license)
- TikTok Commercial Music Library (free, restricted to TikTok ads)
- Custom-composed (start at ~$500 for a 30s loop, scales with rights)
- Trending TikTok sounds — DO NOT use for paid ads (license issues),
  but DO use on organic posts to ride algorithmic boost

SFX checklist for the average 30s casual ad:

- Hook sting (≤ 200ms, low-pitch, attention-grab)
- Tap / click confirmations on UI moments (≤ 80ms each)
- Whoosh / transition sounds on every major cut (~6–10 in a 30s ad)
- Reward chimes on win moments (200–400ms, high-pitch, major chord)
- Bass impact on the emotional peak (~1s tail)
- Logo sting on end card (700–1200ms, recognizable, your audio brand)

Mute design:

- The ad must work fully muted. Period.
- Subtitles cover all dialogue. Sound-effect captions ("WHOOSH",
  "TAP") are optional but trending.
- Visual rhythm should be readable without audio rhythm.

---

## 8. Dialogue & voiceover

If you use VO, follow these:

- Total VO time ≤ 60% of ad length. Silence is allowed and effective.
- Sentences ≤ 8 words. Mobile audiences process short clauses.
- Front-load specifics. "Build a city" not "In this game, you'll be
  able to build cities."
- End with a verb. CTA verbs perform best: Play, Build, Save, Match,
  Beat, Join, Download, Try.
- Read at 130–160 WPM for hype, 90–110 WPM for cinematic, 180+ WPM
  for ironic / casual creator. Match cadence to tone.
- Audition. The same script read by three voice talents will produce
  3× performance variance. Test on small budget first.

Dialogue (in-character / acted):

- If you have actors, give them ONE line and let them improvise around
  it. UGC-style ads outperform polished scripted ones in casual gen-Z.
- Lo-fi mics outperform studio mics for UGC tone. Counterintuitive
  but true — perfect audio reads as "ad" instantly.

---

## 9. On-screen text & subtitles

Subtitles are non-optional. Verbatim captions for all VO/dialogue,
hard-burned into the video (not relying on platform captions).

Text style rules:

- Sans-serif, geometric. Inter, Montserrat, Poppins, Helvetica Bold.
- Minimum size: 64 px equivalent at 1080p (about 40 px on a phone).
- Stroke or shadow for legibility against any background. 2–4 px
  black stroke is the casual default.
- Yellow / white / cream are the highest-readable colors across feeds.
- One text element on screen at a time. Never more than two.
- Animate in (slide, fade, type-on) but hold steady — no
  reading-while-moving.
- Each text block on screen for ≥ 0.8s — minimum reading time even
  for short phrases.
- Use ALL CAPS sparingly — fine for hooks and CTAs, fatiguing for
  sustained subtitles.

On-screen copy that consistently performs in casual:

- Open: "Wait for it…" / "I'm obsessed." / "POV: …" / "99% fail this."
- Mid: "It gets better." / "Then THIS happened." / "And finally…"
- Close: "Play free now" / "Download today" / "Tap to install"

---

## 10. What to reveal, what to hide, what to tease

The discipline of a great video ad is editorial restraint. Not
everything in the game gets equal screen time.

**REVEAL** (show clearly, multiple times)

- The single most photogenic mechanic. Loop it. Let it land.
- The "wow" moment — the screenshot that captures what makes this game
  not-other-games. Show this twice if possible (preview + payoff).
- One unmistakable visual brand element — the King in Royal Match, the
  pig in Coin Master, the Brawler in Brawl Stars, the doge in Save the
  Doge. The viewer should know which game this is by frame 5.
- Social proof if you have it (#1 in Puzzle, 300M players, 5-star).

**HIDE** (omit entirely)

- Tutorials, onboarding, login screens, store/IAP screens.
- Anything the player won't see in their first 5 minutes.
- Loading screens, splash screens, legal text.
- Real game's grindy mid-game loop if you're advertising the punchy
  early-game hook (everybody does this; just be aware of the D7 cost).
- Negative reviews, controversies, complicated pricing.

**TEASE** (show partially, leave the viewer wanting)

- The full progression curve — show level 1 and level 100 cuts, hide
  levels 2–99. Compression of progress is the most powerful teaser.
- Locked content. A clearly marked "?" character or "Coming Soon"
  silhouette creates curiosity without overpromising.
- The depth — flash a multiplayer leaderboard for 0.5s without
  explaining it. Implies "there's more here than you think."
- The community — 0.5s clip of a player reaction, a comment overlay,
  a chat bubble. Implies "people are doing this."
- The personality — character does something charming but unexplained
  (winks, dances, breaks the fourth wall). Tease their world.

The trade test for any element: does it do narrative work in <1s? If
no, cut it. If yes, decide whether to reveal (lots of repetition),
hide (cut entirely), or tease (one ambiguous frame).

---

## 11. The last frame / end card / CTA

The end card is what's on screen when the viewer decides to tap. It
must:

**Composition:**

- Logo in the top half (24–35% from top, large but not huge).
- Tagline below logo, ≤ 6 words, ≥ 64 px.
- Hero character or hero asset on one side, posed and looking toward
  CTA.
- CTA button: bottom 25% of frame, single accent color reserved for
  it.
- Store badges (App Store / Google Play) below CTA, smaller,
  recognizable.
- Background: clean, minimal, on-brand color. Not a busy gameplay
  screenshot.

**Behavior:**

- Hold for 2–3s minimum. Less than 2s and viewers won't process it.
- Subtle motion: pulsing CTA, gentle character idle animation, slow
  background parallax. Not static, not hyperactive.
- Sound: short logo sting if you have one, then quiet. Don't compete
  with the viewer's decision to tap.

**CTA copy that performs (casual game data):**

- "Play Free Now" — safest, broad-appeal default
- "Download Now" — functional, slightly weaker than "Play"
- "Try it Free" — low-commitment framing, performs in EU
- "Join 300M Players" — social-proof variant
- "Install & Play" — highest install intent in some networks
- Imperative verb match — "Build Now" / "Match Now" / "Save the King"

**Avoid:**

- "Click here" — not native to mobile
- "Learn more" — too low-commitment for app install
- Multiple CTAs — one button, one action
- Tiny store badges only — no clear CTA button = lower CTR

---

## 12. Variation strategy

Single-creative campaigns die. Production-grade UA teams ship 10–40
video variants per concept per week. Variation axes, in descending
performance impact:

1. **HOOK** (first 2 seconds). Largest swing — often 3–5× IPM/CTR
   delta between two hooks of the "same" ad. Test 4–8 hook variants
   per concept.
2. **END CARD CTA** copy and button color. 20–40% delta is common.
3. **VOICEOVER** tone (or no VO). Test ironic vs hype vs none on the
   same cut.
4. **MUSIC** track. Same edit, three different tracks. Often 30%+
   swing.
5. **ON-SCREEN TEXT.** Question vs statement vs nothing.
6. **AD LENGTH.** Recut the 30s into a 15s and a 6s bumper.
7. **CASTING** (for live-action / UGC). Three creators saying the same
   line.
8. **PALETTE / FILTER.** Same cut, color-graded warm vs cool vs
   neutral.
9. **ASPECT RATIO** recompositions. Don't just letterbox — re-frame
   for square and horizontal.
10. **CULTURAL LOCALIZATION.** Recast, retranslate, regrade for top
    markets.

Hypothesis-driven, not knob-spinning. Every variant should test a
stated hypothesis ("this hook works on US gen-Z," "this CTA outperforms
imperative verbs in DE"). Random variants are noise.

Iteration cadence: kill bottom 50% of variants every 48–72 hours.
Multiply the top 20% with derivative variants. The half-life of a
winning casual ad is roughly 14–28 days before fatigue.

---

## 13. UGC vs polished — picking the production tier

Three tiers, each with different economics:

**TIER 1 — UGC / Creator-style**
- Cost: $200–2000 per asset. 1–3 day turnaround.
- Format: 9:16 only, handheld or selfie, lo-fi, spoken to camera.
- Wins: TikTok, Reels, Snap. Audiences ≤ 35.
- Loses: YouTube in-stream, Apple Search Ads, mid-core / cinematic
  genres.
- Tools: Insense, Billo, JoinBrands, internal creator network.

**TIER 2 — Mid-fi animated / mixed**
- Cost: $2K–10K per asset. 1–3 week turnaround.
- Format: 2D animated overlays, captured gameplay, light VFX, voiced.
- Wins: Universal — works across all networks. The casual default.
- Loses: Loses to UGC on TikTok feed; loses to cinematic on premium VOD.
- Tools: After Effects, Cavalry, Premiere, captured gameplay reels.

**TIER 3 — Cinematic / VFX / live-action**
- Cost: $25K–500K+ per asset. 4–12 week turnaround.
- Format: Hollywood-grade CGI, celebrity talent, full crew shoots.
- Wins: Brand campaigns, Super Bowl, awards, top-funnel awareness.
- Loses: Performance UA on cost-per-install math. Rarely the right
  call for casual unless you're at $500M+ ARR and need brand.
- Examples: Clash of Clans cinematics ("Revenge"), Coin Master
  celebrity ads, Marvel Snap CGI cinematics, AFK Arena ad films.

Casual game UA mix that consistently wins in 2026:

```
~60% Tier 1 UGC for top-funnel acquisition on TikTok / Reels
~30% Tier 2 mid-fi for cross-network performance
~10% Tier 3 cinematic for brand / retargeting / store-page hero video
```

---

## 14. Emerging trends (2025–2026)

- **EPISODIC / SERIAL ADS** — Last War: Survival and Whiteout Survival
  pioneered 60–120s narrative episodes ("Episode 47"). Viewers
  literally follow campaigns across multiple ads. Drives huge brand
  recall. Translation: think series-of-ads, not standalone-ads.
- **AI-GENERATED EVERYTHING** — Runway, Sora, Veo, Pika for B-roll and
  dream sequences; ElevenLabs / PlayHT for VO; Suno for music. Whole
  casual ads now produced for <$500 by 1 person in 1 day.
- **"FAKE" GAMEPLAY** — exaggerated or partially fabricated gameplay
  sequences that don't exist in the actual game. Industry-controversial,
  network-policed, but still used widely. Risk: store rejection,
  refund waves, brand damage. Use sparingly and disclose where
  required.
- **PARTICIPATIVE FORMATS** — "Comment what level you got to" / "Duet
  this if you survived." Drives engagement signals the algorithm
  rewards.
- **HYPER-VERTICAL CINEMA** — full vertical aspect storytelling with
  proper cinematography for vertical (not horizontal cropped down).
  Whiteout Survival, Last War, Squad Busters all do this.
- **CREATOR-LED BRAND PARTNERSHIPS** — paid posts with creators, then
  whitelisted as paid ads. Highest-converting format for casual
  currently. iSpot / Meta data confirms.
- **SHORT BUMPERS FOR RETARGETING** — 6s ads that ONLY contain the
  end card + a call back to the moment. Used to push warm audiences
  over the line.
- **REVERSE PSYCHOLOGY** — "Don't download this game unless you have
  200 hours to lose." Self-aware and disarming. Effective for puzzle
  and idle.
- **IN-WORLD UGC** — character speaks "from inside the game" directly
  to the viewer. Marvel Snap and Brawl Stars both lean on this.

---

## 15. Case studies — what actually shipped and won

**ROYAL MATCH (Dream Games)**
Format: 15–30s puzzle ads. Tone: earnest hype VO ("Help the King!") +
later ironic-deadpan variants. Hook: pull-pin / fake-fail puzzles
featuring the King in distress. Pacing: rapid 0.7s ASL on the puzzle
moment, 1.5s holds on emotional reveals. Reveal/Hide: shows the puzzle,
hides the match-3 core game. End frame: King smiling with confetti,
"Play Free" CTA.
*Lesson: a single recurring character makes the brand instantly
readable even at thumbnail.*

**LAST WAR: SURVIVAL (FirstFun)**
Format: 60–120s narrative episodes. Tone: cinematic VO + UGC overlay.
Hook: cliffhanger moment ("How did I lose my entire base?"). Pacing:
1.5–2.5s ASL, longer holds for emotional peaks. Reveal/Hide: shows the
dramatic war moments + base building, hides the long mid-game grind.
End frame: epic battle freeze + logo + "Episode 47 — watch more."
*Lesson: serial structure builds parasocial attachment to a
non-existent protagonist; viewers come back to "find out what happens
next."*

**WHITEOUT SURVIVAL (Century Games)**
Format: 60s narrative episodes. Tone: cinematic VO. Hook:
post-apocalyptic survival cliffhanger; child characters in peril.
Pacing: cinematic cuts, weather sound effects carry tone. Reveal/Hide:
reveals dramatic survival moments, hides city-builder mechanics until
late. End frame: snowy city skyline, logo, "Survive Free Today."
*Lesson: emotional weight via children-in-peril is
industry-controversial but undeniably effective in cold-climate
survival games.*

**PROJECT MAKEOVER (Magic Tavern)**
Format: 15–30s. Tone: judgmental friend / mock-UGC. Hook: before-after
split-screen + "she chose THAT?!" reaction. Pacing: 0.8–1.0s ASL on
the dressing montage. Reveal/Hide: reveals dressing-up +
transformation, hides the match-3 core (this caused industry backlash;
Magic Tavern eventually expanded the dress-up loop in-game to fix it).
End frame: glow-up reveal + logo + "Play Free."
*Lesson: emotional rage + transformation is a near-universal hook.*

**COIN MASTER (Moon Active)**
Format: 15–30s + Tier 3 celebrity spots. Tone: hype VO + celebrity
cameo. Hook: celebrity in frame 1 (Cardi B, J.Lo, Ryan Reynolds at
peak). Pacing: variable; celebrity ads slow down for cameo,
hyper-casual variants stay fast. Reveal/Hide: shows the slot machine +
village destruction, hides social/PvP attack mechanics until later.
End frame: celebrity holding phone + game logo.
*Lesson: celebrity ROI is real for casual at top-of-funnel; doesn't
scale forever.*

**STUMBLE GUYS (Scopely)**
Format: 9–30s. Tone: gen-Z ironic / mock-UGC. Hook: stumble fail /
humor moment. POV reactions. Pacing: TikTok-native 0.6s ASL.
Reveal/Hide: shows chaos/multiplayer, hides progression. End frame:
chaotic finish + logo + "Stumble in!"
*Lesson: lean into platform-native tone; don't import broadcast hype
to TikTok feed.*

**CLASH OF CLANS (Supercell)**
Format: 30–120s cinematic Tier 3 (Hog Rider, Revenge, etc.). Hook:
cinematic film-quality opener; villager perspective. Pacing:
film-paced, 2–4s ASL. Reveal/Hide: reveals the world and characters,
barely shows gameplay at all in cinematic cuts (different formats for
performance). End frame: logo + "Free to download."
*Lesson: at the top of the casual market, brand-driven cinematics
carry the brand and a separate performance-creative engine carries
installs.*

**MARVEL SNAP (Second Dinner)**
Format: 15–30s creator-style + Tier 3 cinematic. Hook: card-reveal
moment / creator reaction to a play. Pacing: creator-led, 1–2s ASL.
Reveal/Hide: reveals card art and reactions, hides deck-building
depth. End frame: logo + "Snap it now" / "Play free."
*Lesson: in TCG, the moment of the play is the entire ad; everything
else is texture.*

**SAVE THE DOGE**
Format: 9–15s. Tone: rage-bait + music-only. Hook: dog about to die
in cartoon hazard. Pacing: ultra-fast 0.5s ASL. Reveal/Hide: reveals
the line-drawing mechanic, hides progression. End frame: dog safe +
logo + tap CTA.
*Lesson: weaponized intervention instinct + zero VO = universal-
portable ad that works in 50 markets without translation.*

Pattern across all of them: ONE hook in 2 seconds, one moment in 10
seconds, one feeling carried throughout, one logo at the end.

---

## 16. What to measure

Top-line metrics, in order of decision-making weight:

1. **THUMB-STOP RATE / 3-second view rate.** Does the hook work?
   Casual benchmarks: 25%+ on TikTok, 30%+ on Reels.
2. **AVERAGE WATCH TIME.** Does the body retain? Casual benchmarks:
   8–12s on a 30s ad is healthy.
3. **CTR / TAP RATE.** Does the end card convert intent to action?
4. **IPM** (installs per mille impressions). The composite metric.
5. **CPI** (cost per install). The economic metric.
6. **D1 / D7 RETENTION** of installs from this creative. The honesty
   check.
7. **ROAS D7 / D30.** The ultimate test.

Diagnostic checks when an ad underperforms:

- Low thumb-stop, high CTR → hook is wrong, body is fine.
- High thumb-stop, low CTR → hook is great, end card is broken.
- Mid everything → ad is "fine" — kill it. Mid never wins.
- High IPM, low D1 → bait. Network will throttle within 7–14 days.
- Long-tail CPI rising → creative fatigue. Refresh the hook.

Network reporting tools that matter:

- TikTok Creative Exchange + Symphony Insights.
- Meta Advantage+ creative reporting.
- AppsFlyer / Adjust SKAN-aggregated creative-level data.
- SensorTower / Apptica for competitive creative intelligence (which
  is exactly what `creative_forge` taps into here).

---

## 17. The quick checklist (print this)

- [ ] 9:16 master + 1:1 + 16:9 cuts produced
- [ ] Hook lands in ≤ 2s with one clear subject
- [ ] No logo, no CTA in first 3 seconds
- [ ] Audio designed for muted playback first; VO/music second
- [ ] Hard-burned subtitles for all dialogue
- [ ] Music synced to cuts on the beat
- [ ] One tone of voice, end-to-end
- [ ] One hero element / character recurring throughout
- [ ] One photogenic "moment" in the 5–10s window
- [ ] Variety montage in the middle, max 4–8 micro-clips
- [ ] Emotional peak around 70–80% mark, slowest shot of the ad
- [ ] End card holds 2–3s with logo + tagline + CTA + store badges
- [ ] CTA in single accent color reserved for it
- [ ] Ad reads in <5s of muted scrolling: subject, action, brand
- [ ] Loop test passes — last frame visually flows back into first
- [ ] At least 4 variants ready: 4 hooks × 2 CTAs × 2 music tracks
- [ ] Tested on actual phone, in feed context (not desktop preview)
- [ ] Localized voice talent for top 3 markets, not just translated copy
- [ ] No copyrighted music or assets without paid sync license
- [ ] Compliance: ad makes a promise the actual game can deliver in 5min

---

## 18. Further reading / tools

- SensorTower / Apptica / AppMagic — competitive creative libraries.
- Meta Ads Library — search any advertiser, see all live creatives.
- TikTok Creative Center — top performing ads by region/genre.
- Two & a Half Gamers, Matej Lancaric, Eric Seufert — UA & creative
  teardowns weekly.
- Liftoff / AppsFlyer / Adjust annual mobile creative reports.
- Game UA Camp talks (ChinaJoy, Pocket Gamer Connects, GDC UA Summit).
- "Subscript" / "PocketGamer.biz" creative case studies.
