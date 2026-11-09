#!/usr/bin/env python3
"""Reel Editor web app, by @kemifrank__.
Run locally:  python app.py   then open http://localhost:7860
"""
import os, queue, shutil, sys, tempfile, threading, time
import gradio as gr

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app'))
import pipeline as P

MAX_SECONDS = int(os.environ.get('MAX_SECONDS', '90'))

CSS = """
:root { --cream:#f6efe5; --camel:#c19a6b; --brown:#4a2f23; --ink:#281c16; --yellow:#f8e88e; }
.gradio-container { max-width: 1080px !important; margin: 0 auto !important; background: var(--cream) !important; }
body, .gradio-container { color: var(--ink); }
#hero { text-align:center; padding: 28px 12px 6px; }
#hero h1 { font-family: 'Playfair Display', Georgia, serif; font-size: clamp(34px, 6vw, 56px); font-weight: 700;
           color: var(--brown); margin: 0; letter-spacing: -0.5px; line-height: 1.05; }
#hero h1 em { font-style: italic; font-weight: 500; color: var(--camel); }
#hero p { margin: 10px auto 0; max-width: 560px; font-size: 16px; color: #6b5446; }
#hero .by { font-family: ui-monospace, 'Space Mono', monospace; font-size: 12px; letter-spacing: 2px;
            text-transform: uppercase; color: var(--camel); margin-top: 14px; }
.card { background: #fffaf3 !important; border: 1px solid #e6d8c5 !important; border-radius: 18px !important; }
#go { background: var(--brown) !important; color: var(--cream) !important; font-size: 18px !important;
      border-radius: 14px !important; min-height: 56px; border: none !important; }
#go:hover { background: #5d3c2d !important; }
#status textarea { font-family: ui-monospace, monospace; font-size: 12.5px; background: #fffaf3; }
.step-label { font-family: ui-monospace, monospace; font-size: 12px; letter-spacing: 2px; text-transform: uppercase;
              color: var(--camel); margin: 4px 0 -4px; }
footer { display: none !important; }
"""

BROWN = gr.themes.Color(c50='#f6efe5', c100='#ecdfcc', c200='#dcc6a8', c300='#c9a983', c400='#b08a64', c500='#8a6447',
                        c600='#6e4c36', c700='#5d3c2d', c800='#4a2f23', c900='#3a241b', c950='#281c16')
theme = gr.themes.Soft(primary_hue=BROWN, secondary_hue=BROWN, neutral_hue=gr.themes.colors.stone,
                       font=[gr.themes.GoogleFont('Inter'), 'sans-serif']).set(
    body_background_fill='#f6efe5', block_background_fill='#fffaf3', block_border_color='#e6d8c5',
    input_background_fill='#ffffff', button_primary_background_fill='#4a2f23', button_primary_text_color='#f6efe5',
    checkbox_background_color_selected='#4a2f23', slider_color='#4a2f23',
    block_label_background_fill='#f1e6d6', block_label_text_color='#6e4c36', block_title_text_color='#6e4c36')

HEAD = '<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;1,500&display=swap" rel="stylesheet">'

EFFECT_CHOICES = [(f'{k}  ·  {v}', k) for k, v in P.EFFECTS.items()]
DEFAULT_FX = ['backdrop-word', 'reel-cloud', 'red-collage', 'checklist', 'liquid-glass-graph', 'comment-box']


LANGS = {'English': 'en', 'French': 'fr', 'Spanish': 'es', 'Portuguese': 'pt', 'German': 'de', 'Detect automatically': 'auto'}


def run_edit(video, cut, n_fx, fx_list, zooms, grade, captions, sfx, clean_audio, fixes, lang):
    if not video:
        raise gr.Error('Upload a video first.')
    dur, w, h = P.probe(video)
    if dur > MAX_SECONDS + 1:
        raise gr.Error(f'This version edits videos up to {MAX_SECONDS} seconds. Yours is {dur:.0f}s: trim it and try again.')
    work = tempfile.mkdtemp(prefix='edit_')
    opts = dict(cut_pauses=cut, n_effects=int(n_fx), effects=fx_list or DEFAULT_FX, zooms=zooms, grade=grade,
                captions=captions, sfx=sfx, clean_audio=clean_audio, fixes=fixes, lang=LANGS.get(lang, 'en'))
    q, result = queue.Queue(), {}
    lines = []

    def log(msg): q.put(msg)
    def worker():
        try: result['out'], result['summary'] = P.edit(video, work, opts, log)
        except Exception as ex: result['error'] = str(ex)
        q.put(None)

    threading.Thread(target=worker, daemon=True).start()
    t0 = time.time()
    if h < w: lines.append('Note: vertical videos look best. Landscape works, but effects are designed for 9:16.')
    while True:
        msg = q.get()
        if msg is None: break
        # keep the log readable: steps in full, render progress collapsed to one line
        if lines and msg.startswith('  ') and lines[-1].startswith('  '): lines[-1] = msg
        else: lines.append(msg)
        yield '\n'.join(lines[-14:]) + f'\n\n⏱ {time.time() - t0:.0f}s', None, ''
    if 'error' in result:
        shutil.rmtree(work, ignore_errors=True)
        raise gr.Error(result['error'][-600:])
    final = os.path.join(work, 'edited_reel.mp4'); os.replace(result['out'], final)
    summary = '### Done in {:.0f}s\n'.format(time.time() - t0) + '\n'.join(f'- {s}' for s in result['summary'])
    summary += '\n\nWatch it once before posting: the editor drafts, you approve.'
    yield '\n'.join(lines[-14:]) + f'\n\n✓ Finished in {time.time() - t0:.0f}s', final, summary


with gr.Blocks(title='Reel Editor') as demo:
    gr.HTML("""<div id="hero"><h1>Edit your reel <em>in one tap</em></h1>
        <p>Upload a talking video. Get it back with effects behind your head, captions,
        sound effects and a colour grade, timed to what you say.</p>
        <div class="by">by @kemifrank__ · AI Income Hub</div></div>""")
    with gr.Row(equal_height=False):
        with gr.Column(scale=5):
            gr.HTML('<div class="step-label">1 · your video</div>')
            video = gr.Video(label='Upload (vertical, under 90 seconds)', sources=['upload'], elem_classes='card')
            gr.HTML('<div class="step-label">2 · the edit</div>')
            with gr.Group(elem_classes='card'):
                captions = gr.Dropdown(['House style (lowercase + yellow serif)', 'Word pop', 'Highlight', 'Karaoke',
                                        'Clean subtitle', 'Bold stack', 'Off'], value='House style (lowercase + yellow serif)', label='Captions')
                n_fx = gr.Slider(0, 8, value=4, step=1, label='How many effects')
                sfx = gr.Radio(['Off', 'Subtle', 'Balanced', 'Punchy'], value='Balanced', label='Sound effects')
                cut = gr.Radio(['Off', 'Light', 'Medium', 'Tight'], value='Light', label='Cut pauses')
            with gr.Accordion('More options', open=False):
                fx_list = gr.CheckboxGroup(EFFECT_CHOICES, value=DEFAULT_FX, label='Effects to choose from')
                zooms = gr.Checkbox(value=False, label='Add quick zoom-ins on strong words')
                grade = gr.Dropdown(['None', 'Warm', 'Film', 'Cinematic', 'Moody', 'Editorial', 'Sunset', 'Pastel', 'Pop', 'BW'],
                                    value='None', label='Colour grade')
                clean_audio = gr.Checkbox(value=True, label='Clean up and level the audio')
                lang = gr.Dropdown(list(LANGS), value='English', label='Language spoken in the video')
                fixes = gr.Textbox(label='Fix misheard words (optional)', placeholder='ChargeGPT=ChatGPT, Cloud=Claude')
            go = gr.Button('Edit my video', elem_id='go', variant='primary')
        with gr.Column(scale=5):
            gr.HTML('<div class="step-label">3 · your edited reel</div>')
            out = gr.Video(label='Edited reel', interactive=False, elem_classes='card')
            summary = gr.Markdown()
            status = gr.Textbox(label='Progress', lines=9, max_lines=16, interactive=False, elem_id='status')
    go.click(run_edit, [video, cut, n_fx, fx_list, zooms, grade, captions, sfx, clean_audio, fixes, lang], [status, out, summary])

if __name__ == '__main__':
    demo.queue(default_concurrency_limit=1, max_size=20).launch(
        server_name='0.0.0.0', server_port=int(os.environ.get('PORT', 7860)), max_file_size='300mb',
        theme=theme, css=CSS, head=HEAD)
