---
name: effects
description: Edit talking-head videos: cut fillers and mistakes, auto colour grade, captions, 108 effects, sound effects, B-roll and zooms. Use for /effects or any request to edit a video.
---

# Effects: 107 video effects, captions, clean cuts and grading (by @kemifrank__)

The user is usually not technical. Keep replies short and friendly, do the work for them, and never ask them to run commands themselves.

All paths below are relative to this skill's folder (the folder this SKILL.md is in). Use its absolute path in commands.

## 1. First run: set up (once)
Run `bash scripts/setup.sh`. It prints `READY` when done (the first time takes 1 to 3 minutes).
- `NEED_FFMPEG`: install it for them. On a Mac: `brew install ffmpeg` (if `brew` is missing, tell them to install Homebrew from brew.sh first). On Windows: `winget install ffmpeg`.
- `NEED_PYTHON`: install Python 3.12 (Mac: `brew install python@3.12`, Windows: `winget install Python.Python.3.12`), then run setup again.
- On Windows, the Python is at `.venv\Scripts\python.exe` instead of `.venv/bin/python`.

## 2. Get the video and the effect
- Video: the user drags the file into the chat, or gives a path. A vertical phone video works best.
- Effect: from `/effects <name>`, or from what they describe. Match their words to the table below. Unsure? Show them the list.

## 3. Find the timing
- If they say "on the word X" or "when I say ...", run `.venv/bin/python scripts/words.py <video>` and use those times.
- If they give no timing, apply the effect for the whole clip, or ask which part (one short question).
- Short windows look best: 1.5 to 4 seconds per effect.

## 4. Draft, check, render
1. Write the plan next to their video as `<video-name>_effects.json`:
   ```json
   {"effects": [
     {"fx": "orbit", "start": 3.2, "end": 6.0},
     {"fx": "backdrop-word", "start": 14.0, "end": 16.3, "text": "AI"}
   ]}
   ```
2. Check frames first (fast): `.venv/bin/python scripts/fx.py --plan <plan.json> <video> <folder>/check.png --still 4.5,15.2`, using the middle of each effect. Look at the PNGs yourself. Fix the text, timing or options if something looks off (covers the face, cut off by the edge, unreadable).
3. Render: `.venv/bin/python scripts/fx.py --plan <plan.json> <video> <video-name>_effects.mp4`. The output keeps their original audio. It renders at 1080p by default; add `--width 2160` for 4K (slower).
4. Tell them where the file is. Remind them in one line to watch it before posting: it drafts, they approve.

A single effect needs no plan: `.venv/bin/python scripts/fx.py orbit <video> <out.mp4> --start 3 --end 6 --text "..." --opt key=value`.

## The 108 effects
| # | `fx` name | What it does | Options (all optional) |
|---|---|---|---|
| 1 | `noise` | Reels pile up behind your head, one every quarter second | `images` (folder of screenshots or clips), `size` |
| 2 | `lineup` | Numbered tiles fan out in an arc above your head | `text` (tile names joined with `\|`) |
| 3 | `locked-on` | Corner brackets snap onto your face, the camera follows you | `zoom` (default 1.35), `text` (tag) |
| 4 | `orbit` | Your reels circle your head: in front at the bottom, behind at the top | `images`, `count`, `speed`, `size` |
| 5 | `lean-in` | A fast punch-in on one word | `zoom` (default 1.45, max 2), `speed` |
| 6 | `backdrop-word` | A giant word drops in behind you | `text`, `color` (hex), `font` (`bold` or `serif`) |
| 7 | `spotlight` | Kills the lights, keeps you lit | `text` (glowing word behind you), `color`, `push` |
| 8 | `the-bill` | Prints your instructions like a receipt into the wall above your head | `text` (lines joined with `\|`) |
| 9 | `moody` | A moody colour grade | `grade` (`moody`, `bw`, `warm`, `cool`, `pop`) |
| 10 | `swipe` | A before and after slider sweeps across you | `grade` (the "after" look) |
| 11 | `todo` | A checklist card beside your head ticks off as you talk | `text` (items with `\|`), `ticks` (video seconds with `\|`), `title` |
| 12 | `comment-box` | An Instagram comment bar types a word and posts it | `text` (default EFFECTS) |
| 13 | `tap` | A Follow button pops up and flips to Following | `at` (video second of the flip), `x`, `y` (0 to 1), `color` |
| 14 | `pause-point` | Freezes the frame and points at you with a hand-drawn arrow | `text` (label), `color`, `label_x` |
| 15 | `uninstall` | A glitchy uninstall bar breaks the frame apart | `text` |
| 16 | `reel-frame` | Your video shrinks into an Instagram reel card | `text` (handle) |
| 17 | `shortcut-rain` | Keyboard keys rain down behind you | `text` (keys with `\|`), `count` |
| 18 | `reject-stamp` | A big red stamp slams onto the screen | `text`, `color`, `angle`, `y` |
| 19 | `countdown-flip` | A 3, 2, 1 flip clock above your head | `from` |
| 20 | `rabbit-hole` | The frame tunnels into itself, spinning | `ratio`, `speed`, `spin` |
| 21 | `cover-star` | You become a magazine cover, title behind your head | `text` (title), `lines` (with `\|`), `issue`, `color` |
| 22 | `scribble` | Marker doodles draw themselves around you | `text` (label), `color` |
| 23 | `glass-widgets` | Frosted glass widgets and mini artifacts float around your head, plus a Made with AI pill | `text` (big number), `name`, `handle`, `look` (`simple` for the 3-widget version) |
| 24 | `red-collage` | Black and white you, a giant red word behind, three lines slam in | `text` (red word), `lines` (with `\|`), `tag` |
| 25 | `split-headline` | A headline card slides down and pushes you to the bottom half | `text` (lines with `\|`), `hl` (highlighted word), `pill` |
| 26 | `pastel-word` | Lavender room, giant word behind you, a profile card gets followed | `text`, `name`, `handle` |
| 27 | `check-pills` | Grid-paper room, reel boards behind you, a cursor clicks blue pills | `text` (pills with `\|`), `images` |
| 28 | `timeline` | A dark red film grade with an editing timeline, a REC timecode and a glowing playhead | `text` (title), `sub`, `tc` |
| 29 | `headline-box` | A punch-in with a two-line headline, the second line in a white box | `text` (lines with `\|`), `zoom` |
| 30 | `profile-wall` | Your reels grid fills the wall behind you while a counter ticks up | `images`, `count`, `label` |
| 31 | `tier-list` | A tier list drops in and AI flies into S tier | `title`, `item`, `others` |
| 32 | `broll-split` | B-roll on top with a price-tag sticker, you below | `images`, `text` (tag) |
| 33 | `phone-fan` | Your reels fan out like a hand of phones under a headline | `images`, `text` (lines with `\|`) |
| 34 | `dot-reveal` | Your shot builds out of glowing dots, then snaps to the full picture | `color`, `cell` |
| 35 | `headline-wall` | Your own headlines pile up behind your head, then a total pops in front | `text` (`headline::meta\|...`), `total`, `label` |
| 36 | `checklist` | A task list under your chin: each step spins, then ticks green | `text` (`step::meta\|...`), `title` |
| 37 | `liquid-glass-graph` | A liquid glass card under your chin: a green graph climbs while the number counts up | `text` (label), `from`, `to` (e.g. `197K`, `59%`), `color` |
| 38 | `carousel-spin` | Your reels spin around you in a 3D carousel, then slow to a stop | `images`, `count`, `size`, `turns` |
| 39 | `match-cut` | News pages cut on one word, locked in a red box behind your head | `text` (the word, default AI), `color` |
| 40 | `apple-toggles` | An iPhone settings card under your chin flips its switches on, one line at a time | `text` (rows with `\|`), `ticks` (seconds with `\|`), `color` |
| 41 | `led-sign` | The lights drop and a glowing LED sign types itself out behind you | `text` (lines with `\|`), `color`, `push` |
| 42 | `slow-push` | A slow cinematic push-in to your face while the room melts out of focus | `zoom` (default 1.6), `blur` |
| 43 | `reel-cloud` | Your reels float around your head (upper ones tucked behind it, two in front) under a two-line headline in black boxes | `text` (2 lines with `\|`), `views` (real counts with `\|`, optional), `size`, `y` |
| 44 | `stacked-words` | Three words stack up behind your head, each in a different font | `text` (3 words with `\|`), `color` |
| 45 | `word-rain` | Your word rains down behind you in every size | `text`, `color`, `font` |
| 46 | `outline-echo` | A giant word with outline echoes pulsing out behind your head | `text`, `color`, `font` |
| 47 | `neon-word` | A neon tube word flickers on behind your head | `text`, `color`, `font` |
| 48 | `script-word` | A word writes itself in pretty script behind your head | `text`, `color`, `font` |
| 49 | `bubble-word` | A squishy bubble-letter word bounces in behind your head | `text`, `color`, `font` |
| 50 | `sticker-word` | A word slaps on like a sticker beside your face | `text`, `color` (sticker colour), `font` |
| 51 | `letter-drop` | The letters of a word drop in one by one and bounce | `text`, `color`, `font` |
| 52 | `marquee` | A scrolling ticker band of your text runs behind you | `text`, `color`, `font` |
| 53 | `big-number` | A huge number counts up behind your head | `to` (e.g. `100K`, `$5,000`), `label`, `color` |
| 54 | `quote-card` | A glass quote card with your words slides up under your chin | `text` (the quote), `name`, `font` |
| 55 | `highlight-words` | Three key words pop up around your head in marker boxes | `text` (3 words with `\|`), `font` |
| 56 | `side-titles` | Tall magazine titles run up both sides of the frame | `text` (2 words with `\|`), `color` |
| 57 | `speech-bubble` | A comic speech bubble pops out beside your face | `text`, `font` |
| 58 | `thought-bubble` | A fluffy thought cloud floats above your head | `text`, `font` |
| 59 | `arrows-in` | Hand-drawn arrows sketch in from both sides, pointing at you | `text` (optional label), `color` |
| 60 | `doodle-crown` | A hand-drawn crown sketches itself onto your head | `color` |
| 61 | `sparkles` | Twinkling sparkles dance around your head | `color` |
| 62 | `confetti` | A burst of confetti pops and flutters down | none |
| 63 | `vhs` | A retro VHS look: scanlines, colour bleed and a REC timestamp | none |
| 64 | `light-leak` | A warm film light leak washes across the frame | `color` |
| 65 | `film-burn` | An orange film-burn flash, great as a transition | none |
| 66 | `bw-pop` | The room turns black and white while you stay in full colour | none |
| 67 | `color-room` | Your background turns one bold colour while you stay natural | `color` |
| 68 | `bokeh` | Soft glowing bokeh lights drift behind you | none |
| 69 | `dream-glow` | A soft, dreamy glow with lifted haze | none |
| 70 | `strobe` | Quick white flashes on the beat | `count` |
| 71 | `duotone` | The whole frame becomes a two-colour poster look | `color` (light), `dark` |
| 72 | `portrait-blur` | Portrait mode: the background melts into soft blur | none |
| 73 | `rgb-glitch` | A digital RGB-split glitch with tearing bands | none |
| 74 | `shake` | A short handheld camera shake for impact (no zoom) | `amount` |
| 75 | `flash` | A clean white flash, the classic cut transition | `color` |
| 76 | `polaroid` | Your shot shrinks into a tilted polaroid photo with a handwritten caption | `text` (caption), `color` (background), `font` |
| 77 | `phone-frame` | You shrink into a phone screen, like a reel inside a reel | `text` (title above), `color` |
| 78 | `window-frame` | You appear inside a desktop app window with traffic-light buttons | `text` (window title), `color` |
| 79 | `film-strip` | Film-strip borders with sprocket holes roll down the sides | none |
| 80 | `cinema-bars` | Cinema bars slide in with a title, like a movie trailer | `text` (title), `font` |
| 81 | `grid-split` | Your shot multiplies into a 3x3 grid, then snaps back | `count` (grid size, default 3) |
| 82 | `notifications` | Phone notifications stack in above your head, one by one | `text` (`title::detail\|...`) |
| 83 | `dm-bubbles` | Chat bubbles pop in like a DM conversation beside you | `text` (messages with `\|`, alternating sides) |
| 84 | `search-bar` | A search bar types your question, with suggestions dropping down | `text` (the search) |
| 85 | `poll` | A poll sticker appears and the votes fill up live | `text` (`question\|option A\|option B`), `to` (percent for A) |
| 86 | `progress-bar` | A glossy progress bar fills up with a label and percent | `text` (label), `to` (percent), `color` |
| 87 | `stat-cards` | Three stat cards pop up in a row under your chin | `text` (`value::label\|...`, 3 items), `font` |
| 88 | `calendar` | A calendar page pops in and a date gets circled | `text` (month), `day` |
| 89 | `price-tag` | A price tag swings in on a string beside you | `text` (price), `color`, `font` |
| 90 | `before-after` | A BEFORE / AFTER split with a sliding divider and labels | `text` (2 labels with `\|`), `grade` (the before look) |
| 91 | `subscribe` | A red Subscribe button gets clicked, then a bell rings | `at` (seconds into the effect when it is clicked), `text` |
| 92 | `like-burst` | A big heart pops, then little hearts burst and float up | `color` |
| 93 | `star-rating` | Five stars fill in one after another with a rating | `to` (stars, 1 to 5), `text` (label) |
| 94 | `timer-ring` | A circular countdown ring ticks down beside you | `from` (seconds), `color` |
| 95 | `email-pop` | A new email card slides down with a subject line | `text` (`sender::subject`) |
| 96 | `quiz-card` | A quiz card appears and the right answer lights up green | `text` (`question\|A\|B\|C`), `answer` (1 to 3) |
| 97 | `money-rain` | Bills and coins rain down behind you | `symbol` (e.g. `₦`) |
| 98 | `location-pin` | A map pin drops in with the name of a place | `text` (place) |
| 99 | `now-playing` | A music player card with a moving waveform: now playing | `text` (`song::artist`) |
| 100 | `sticker-pack` | Cute stickers (heart, star, smiley, "wow") slap on around you one by one | `text` (the word sticker) |
| 101 | `text-card` | Editorial: a full-screen cream or green card where serif words blur in as you speak | `text` (markup below), `theme` (`cream`, `green`), `times` (word times in seconds into the effect, with `\|`), `y` |
| 102 | `serif-words` | Editorial: serif words blur in over your video, just below your chin | `text` (markup), `times`, `y`, `color` |
| 103 | `split-card` | Editorial: a card on top with a title and list pills, your video slides into a rounded frame below | `text` (title, markup), `items` (pills with `\|`), `item_times`, `theme` |
| 104 | `dual-frame` | Editorial: a close-up of you on top and the wide shot below, like two cameras | `zoom` (default 1.35) |
| 105 | `clean-zoom` | A smooth, eased zoom into your face that holds, drifts slightly, then eases back out | `zoom` (default 1.28), `ease` (seconds, default 0.45; 0 = instant cut-zoom), `out` (`false` to stay zoomed) |
| 106 | `stat-grid` | Editorial: a green card with a big number counting up over a grid that fills in | `to`, `text` (line above, markup), `theme` |
| 107 | `cta-quote` | Editorial: Comment “WORD” in big serif with a small line under it, blurring in | `text` (the keyword), `sub`, `times`, `y` |
| 108 | `side-list` | **Wide (16:9) videos:** a list builds beside you, one item as you say it (tools, steps, names) | `items` (a\|b\|c), `item_times` (seconds after start, a\|b\|c), `title`, `look` (glass, cream, chat), `side` (auto, left, right), `numbers` (yes/no), `size` |

**Named looks** (same effect, a fancier look; they don't add to the count):
- `glitter-spotlight` = `spotlight` with `look=sparkle`: the room goes dark, golden rays burst from behind your head, a big gold word with a shine sweep, twinkling sparkles and a glow around you. `text` (the word), `color`, `push`.
- `cover-star` with `look=editorial`: a soft warm film look, a classic serif masthead behind your head, an issue line and elegant cover lines. `text` (masthead), `issue`, `lines` (3 lines with `\|`), `right` (lines with `\|`), `color`, `accent`, `lines_y`, `right_y`.
- `liquid-glass-graph` with `look=bento`: the climbing graph moves to a smoked glass screen behind your head, with glass bento tiles in front of you (a donut, a KPI, bars). `text`, `from`, `to`, `donut` (`29%::label`), `kpi` (`672K::label`), `bars` (`197\|140\|124::label`).
- `apple-toggles` now sits above you, tucked behind your head, with a gentle zoom (`pos=below` for the old under-the-chin card; `overlap`, `zoom`).

Aliases work too: `bill`, `to-do`, `follow`, `stamp`, `countdown`, `cover`, `rain`, `pause`.

**Font option.** Most effects that draw words take `font`. Cute fonts: `fredoka`, `baloo`, `chewy`, `sniglet`, `cherry`, `gluten`, `grand`, `playpen`; scripts: `pacifico`, `caveat`, `dancing`, `lobster`, `gochi`; bold display: `shrikhand`, `bungee`, `righteous`, `brico`, `anton`; elegant: `dmserif`, `didone`, `serif`.

**Placement.** Words sit behind the head; cards sit under the chin or beside the face and never cover it. On tight framing everything moves to stay inside the frame. Frame effects (`polaroid`, `phone-frame`, `window-frame`, `grid-split`) take over the whole picture, so captions hide while they play.

## The editorial look (cream + forest green)

Use this when the user asks for the "editorial", "cream and green", "aesthetic", "serif" or "clean" style, or shares a reel like that. Use only the user's own footage.

- Captions: `--style serif-mid`. Serif words blur in just below the chin; the key word turns big italic.
- Every 6 to 10 seconds, cut to a `text-card` (alternate `theme` `green` and `cream`) for the key line of the script. Use `times` from words.py so each word lands as it is spoken.
- Lists ("three things", "the steps") go in a `split-card` with `items`, timed with `item_times`.
- Numbers go in `stat-grid`. The final call to action goes in `cta-quote`.
- Zooms: `clean-zoom` (1.2 to 1.35) on strong lines, held for 2 to 4 seconds; `dual-frame` once or twice for variety. No shakes, no flashes, no stickers in this look.
- Sounds: only soft whooshes and swooshes (the `sfx.py auto` defaults for these effects).

Text markup for these effects: `*word*` or `*several words*` = italic accent, `**WORD**` = big bold, `|` = new line.

## 5. Captions (house style: `editorial`)

Always use the `editorial` style unless the user asks for another one. It's the default.

The look: lowercase white sans, big, with a soft shadow and no box. The key word of each phrase (the punchline, a name or a number) is set in a pale-yellow italic serif on its own line. Words appear as they're spoken. The block sits just above the head, so the head passes in front of the bottom of the words.

1. Get the words: `.venv/bin/python scripts/words.py <video>` writes `<video>.words.json`. Read it and fix any misheard words (brand names especially: "ChargeGPT" means ChatGPT).
2. Render: `.venv/bin/python scripts/captions.py <video> <out.mp4> --words <video>.words.json --fx-plan <plan.json>`
   - `--fx-plan` moves captions to the bottom while an effect is using the space above the head. Under-the-chin effects (`checklist`, `liquid-glass-graph`) keep captions above the head.
   - `--bottom-at "19-21.6,39.6-43"` adds extra bottom-caption windows: B-roll cutaways, a text hook, any overlay above the head.
   - `--emphasis "claude,edited"` forces which words get the yellow serif. Otherwise they're picked automatically and used sparingly.
   - `--fix "ChargeGPT=ChatGPT"` is a quick word fix without editing the JSON. `--no-behind` keeps the words in front of the head.
3. Check a few frames: no word should vanish behind the head, and nothing should be cut off at the top.

Landscape (16:9 YouTube) is handled automatically. For wide videos, use effects that live beside or behind the speaker: `side-list`, `backdrop-word`, `search-bar` (with `suggest=none`), `clean-zoom`. Captions sit in one low line with the yellow serif word inline, over a soft dark fade at the bottom of the frame. They never go behind the head, because a landscape frame has no room above it. The vertical-reel effects in `fx.py` don't fit 16:9 (they overlap the face or get cut off), so for landscape use side cards in the empty space left and right of the speaker instead.

**Placement rules (automatic):**
- Reels and TikTok safe zone: text stays above the bottom 20% (the username and caption area), below the top 10%, and inside 80% of the width, clear of the like/comment buttons.
- Positions are sticky: a caption reuses the last spot unless the face really moved, so text doesn't jump between phrases.
- Lines are balanced, so a single word is never left alone on a line.
- If the face fills the top of the frame (a close-up), the caption moves below the chin instead of being squashed at the top.

Other styles (only when the user asks, or names one):
- `bubbly`: Round white letters with a pink outline, key word in yellow
- `sticker`: Every word on its own little sticker, key word on yellow
- `handwritten`: Soft handwriting, key word in pink script
- `candy`: Chunky pastel 3D letters
- `neon`: Glowing neon tube letters, key word in hot pink
- `boxed`: White words on black rounded boxes, key word in yellow
- `marker`: A yellow highlighter swipes behind the key word
- `typewriter`: Letters type out one by one with a cursor
- `luxe`: Elegant serif with a gold script key word
- `retro`: 70s chunky letters with a brown drop shadow
- `comic`: Comic-book capitals with a black outline, key word in red
- `soft-pill`: Friendly words on a soft pastel pill
- `wavy`: Bouncy letters that gently wave
- `cherry`: Bubble letters in cherry pink with a white outline
- Classic: `word-pop`, `highlight`, `karaoke`, `clean`, `bold-stack` (with `--color`, `--position`, `--max-words`).

The new styles run through the same engine as the house style: words appear as spoken, a key word is picked automatically (or with `--emphasis`), `--fx-plan` moves them out of the way of effects, and `--position top/center/bottom` overrides where they sit.

## 6a. Clean cut (fillers, mistakes, retakes): do this FIRST on any raw recording

`.venv/bin/python scripts/clean.py <video> <clean.mp4>` removes um/uh/er/hmm, stutters ("I I think"), cut-off words, false starts and retakes (it keeps the LAST take, the one you got right), plus untranscribed noises between words, and tightens pauses.

It writes three files:
- `<clean>.mp4`: the clean video.
- `<clean>.words.json`: word timings already remapped to the cut. Pass it straight to `captions.py --words`, so there's no need to run words.py again.
- `<clean>.review.txt`: every cut with its reason, plus the clean script.

1. Run with `--dry-run` first and read the review list out to the user (cuts + `CHECK` lines). `CHECK` means a word lasts suspiciously long and may hide a repeat. Watch that spot.
2. Adjust: `--keep 12-14` undoes a cut (word numbers come from the review list); `--cut 40-44` forces one. `--aggressive` also removes "you know", "I mean", "basically", "literally", "kind of". `--max-gap 0.3` sets the longest pause kept. `--no-retakes` keeps every take.
3. Render without `--dry-run`.

How it works: speech is split at pauses and each chunk is transcribed on its own, verbatim. Normal Whisper hides mistakes by merging a false start and its retake into one tidy sentence. Verified on a spliced test (false start + stutter, both caught) and on a clean 2-minute talk (0 good words cut).

## 6. Cuts (remove dead space)

Run `.venv/bin/python scripts/cuts.py <command> <video> <output.mp4>`.

Commands:
- `cut-silence` — detect and remove silent gaps. Options: `--threshold` (dB, default -30), `--min-silence` (seconds, default 0.5), `--padding` (seconds, default 0.05).
- `jump-cut` — aggressive mode, removes all pauses > max_gap. Options: `--max-gap` (seconds, default 0.25).
- `trim` — simple start/end trim. Options: `--start`, `--end` (seconds).

Example: `.venv/bin/python scripts/cuts.py cut-silence video.mp4 cut.mp4 --threshold -35 --min-silence 0.4`

## 7. B-roll (insert B-roll clips)

Run `.venv/bin/python scripts/broll.py <mode> <video> <output.mp4> --broll <clip> --at <seconds> --duration <seconds>`.

Modes:
- `cutaway` — full-screen B-roll with fade transition.
- `pip` — picture-in-picture in a corner. Options: `--corner tl/tr/bl/br`, `--pip-scale` (default 0.35).
- `split` — top/bottom or left/right split screen. Options: `--orientation tb/lr`.
- `overlay` — B-roll blended into background behind person.

For multiple B-rolls, use `--plan broll.json` with a JSON array of insertions.

Supports video and image B-roll sources (images repeat as static, videos loop if shorter).

## 8. Color Grading (auto + 12 looks)

**Default: `auto`.** `.venv/bin/python scripts/grade.py auto <video> <graded.mp4>` measures the whole clip once and fixes:
- white balance, from neutral pixels only, so skin never pulls it cool;
- black and white levels;
- exposure, with a highlight roll-off so foreheads and lamps never blow out;
- skin-safe vibrance;
- a gentle contrast curve.

The same correction is applied to every frame, so there's no flicker. It prints what it measured.

Add a look on top: `grade.py auto in.mp4 out.mp4 --look warm --look-strength 0.5` (any preset below). Always correct first, then style; never put a look on uncorrected footage.

Or a look alone: `.venv/bin/python scripts/grade.py <preset> <video> <output.mp4>`.

Presets: `moody`, `warm`, `cool`, `film`, `pop`, `bw`, `vintage`, `cinematic`, `sunset`, `editorial`, `neon`, `pastel`.

Options: `--strength` (0-1, default 1.0), `--grain` (film grain, try 0.02), `--vignette` (darkened edges, try 0.3), `--letterbox` (cinemascope bars, e.g. 2.35).

Example: `.venv/bin/python scripts/grade.py cinematic video.mp4 graded.mp4 --strength 0.8 --grain 0.02 --vignette 0.3`

Use `--list` to see all available grades.

## 9. Speed Ramps (slow-mo, speed up, timelapse)

Run `.venv/bin/python scripts/speed.py <command> <video> <output.mp4>`.

Commands:
- `ramp` — smooth speed change at a moment. Options: `--at` (center second), `--duration`, `--speed` (0.3 = slow-mo, 2.0 = fast). Use `--plan speed.json` for multiple ramps.
- `slow-mo` — slow down a section. Options: `--start`, `--end`, `--speed` (default 0.4).
- `speed-up` — speed up a section. Options: `--start`, `--end`, `--speed` (default 2.0).
- `timelapse` — speed up the entire video. Options: `--speed` (default 4.0).

Example: `.venv/bin/python scripts/speed.py slow-mo video.mp4 slowmo.mp4 --start 2.0 --end 4.0 --speed 0.3`

## 10. Sound effects (always add them to a full edit)

Default style is `designed`: polished, moderate sounds from the CC0 packs in `assets/sfx/packs`. Use `studio` for most cues, `cinematic` for transitions and big moments, and `soft` or `zen` for gentle ones. Any pack sound can be used directly, e.g. `{"sfx": "studio/send", "at": 4.2}`. Typing stays synthesized because the user likes it. Keep it moderate: avoid heavy impacts and bass beds unless asked. `--style synth` brings back the original synthesized set.

Every sound is synthesized by `scripts/sfx.py`, so there's nothing to download and no licences to worry about. They're mixed under the voice (about 6 dB below speech by default).

- Auto: `.venv/bin/python scripts/sfx.py auto <video> <out.mp4> --fx-plan <plan.json> --extra <extra.json> --save-plan <sfx_used.json>`. This matches a sound to every effect in the plan, timed to its animation (impact when a backdrop word lands, ticks on checklist items, typing plus a chime on the comment box, a clunk when the lights drop, and so on).
- `--extra` covers things that aren't in the fx plan: an impact on the opening hook, a whoosh about 0.2s before each B-roll cutaway and a swoosh as it leaves, typing on any typed text, a riser under a slow zoom, a ding or cash on results and numbers. Format: `[{"sfx": "whoosh", "at": 18.8, "vol": 0.8}, {"sfx": "typing", "at": 19.6, "dur": 1.4}]`.
- Exact times only: `sfx.py add <video> <out.mp4> --plan sfx.json`.
- Loudness: `--level` (default 0.35; 0.5 is punchier, 0.2 is subtle). Keep the voice on top.
- `sfx.py list` shows all 25 sounds. They're also saved as .wav files in `assets/sfx/` for the user to drag into CapCut.

Sounds: whoosh, swoosh, whoosh-long, swipe, pop, bubble, tick, click, ding, chime, cash, impact, thud, stamp, riser, shimmer, typing, shutter, glitch, clunk, buzz, scribble, scratch, heartbeat, sub (low bass bed under a hook).

Plus 12 designed packs in `assets/sfx/packs`, about 70 sounds each: `studio`, `cinematic`, `soft`, `zen`, `rubber` (bouncy, cute), `arcade` (game rewards), `dreamy`, `glass`, `mechanical`, `minimal`, `organic`, `scifi`. Use any as `pack/name`, e.g. `rubber/snap`, `arcade/achievement`, `dreamy/reward`, `studio/notification`. Every one of the 100 effects has a matching sound in `sfx.py auto`. The user prefers moderate sounds: keep typing and whooshes, avoid watery pops unless asked.

## Full edit order
1. Clean cut (`clean.py`): fillers, mistakes, retakes, pauses. Show the review list.
2. Fix any misheard words in `<clean>.words.json` (no need for words.py).
3. Effects (`fx.py`).
4. B-roll, zooms, text hook.
5. Grade (`grade.py auto`, plus `--look` if wanted). Do this before captions so the text colours stay true.
6. Captions (`captions.py --words <clean>.words.json`).
7. Sound effects (`sfx.py`) last, because it only remixes the audio.

## Rules
- Never cover the face. Everything either goes behind the person or avoids the face by itself; if a check frame still shows text over the face, move it (`x`, `y`) or shorten the text.
- Effects run in the order listed. Put camera effects (`locked-on`, `lean-in`, `spotlight`) first when they overlap others.
- Zoom never goes past 2x, so the video stays sharp.
- These are starter versions. Be honest about that if the user compares them to a reel they saw.
