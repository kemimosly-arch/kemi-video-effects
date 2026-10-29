---
name: effects
description: Edit talking-head videos: 42 visual effects, house-style captions, sound effects, B-roll, cuts, grading and speed ramps. Add any of 42 video effects to a talking-head video (orbit, spotlight, glass widgets, timeline, checklist, headline wall, comment box, phone fan, liquid glass graph, match-cut, iPhone toggles, LED sign and more). Effects track the speaker's face and can sit behind their head. Use when the user types /effects, names one of the effects, or asks to add an effect, zoom, grade, sticker or animation to their video.
---

# Effects: 42 video effects (by @kemifrank__)

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

## The 42 effects
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

**Named looks** (same effect, a fancier look; they don't add to the count):
- `glitter-spotlight` = `spotlight` with `look=sparkle`: the room goes dark, golden rays burst from behind your head, a big gold word with a shine sweep, twinkling sparkles and a glow around you. `text` (the word), `color`, `push`.
- `cover-star` with `look=editorial`: a soft warm film look, a classic serif masthead behind your head, an issue line and elegant cover lines. `text` (masthead), `issue`, `lines` (3 lines with `\|`), `right` (lines with `\|`), `color`, `accent`, `lines_y`, `right_y`.
- `liquid-glass-graph` with `look=bento`: the climbing graph moves to a smoked glass screen behind your head, with glass bento tiles in front of you (a donut, a KPI, bars). `text`, `from`, `to`, `donut` (`29%::label`), `kpi` (`672K::label`), `bars` (`197\|140\|124::label`).
- `apple-toggles` now sits above you, tucked behind your head, with a gentle zoom (`pos=below` for the old under-the-chin card; `overlap`, `zoom`).

Aliases work too: `bill`, `to-do`, `follow`, `stamp`, `countdown`, `cover`, `rain`, `pause`.

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

Landscape (16:9 YouTube) is handled automatically. Captions sit in one low line with the yellow serif word inline, over a soft dark fade at the bottom of the frame. They never go behind the head, because a landscape frame has no room above it. The vertical-reel effects in `fx.py` don't fit 16:9 (they overlap the face or get cut off), so for landscape use side cards in the empty space left and right of the speaker instead.

Other styles (only when asked): `word-pop`, `highlight`, `karaoke`, `clean`, `bold-stack`, with `--color`, `--position top/center/bottom`, `--max-words`.

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

## 8. Color Grading (12 presets)

Run `.venv/bin/python scripts/grade.py <preset> <video> <output.mp4>`.

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

## Full edit order
1. Cut dead space (`cuts.py`), if wanted.
2. Run `words.py` and fix the words.
3. Effects (`fx.py`).
4. B-roll, zooms, text hook.
5. Captions (`captions.py`, editorial).
6. Sound effects (`sfx.py`) last, because it only remixes the audio.
7. Grade (`grade.py`), if wanted, before captions so the text stays clean.

## Rules
- Never cover the face. Everything either goes behind the person or avoids the face by itself; if a check frame still shows text over the face, move it (`x`, `y`) or shorten the text.
- Effects run in the order listed. Put camera effects (`locked-on`, `lean-in`, `spotlight`) first when they overlap others.
- Zoom never goes past 2x, so the video stays sharp.
- These are starter versions. Be honest about that if the user compares them to a reel they saw.
