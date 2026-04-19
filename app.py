from dash import Dash, html, dcc, Input, Output, State, no_update, ctx, ALL
from dash.exceptions import PreventUpdate

# local imports
from config import LINKEDIN, GITHUB, EMAIL, COLORS
from data_loader import (
    df_emb, top_products, brackets,
    TOTAL_REVIEWS, AVG_RATING, POS_PCT, NEG_PCT, UNIQUE_PRODUCTS
)
from charts import sentiment_trend_fig, price_bracket_fig, sentiment_donut_fig, product_trend_fig
from rag import run_rag, rewrite_query, retrieve, generate_pros_cons, summarize_chart, compare_products
from components import hero_stat, section_head, product_row, chart_panel, modal, footer

app = Dash(__name__, suppress_callback_exceptions=True)
app.title = 'Review Intelligence'

# inject fonts + counter/scroll scripts (assets/style.css auto-loads)
app.index_string = '''
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{%title%}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
{%favicon%}{%css%}
</head>
<body>
{%app_entry%}
{%config%}{%scripts%}{%renderer%}
<script>
function animateCounter(el, target, duration=1400, suffix='', decimals=0) {
  const start = 0; const t0 = performance.now();
  function tick(now) {
    const p = Math.min(1, (now-t0)/duration);
    const eased = 1 - Math.pow(1-p, 3);
    const val = start + (target-start)*eased;
    el.textContent = val.toLocaleString(undefined,{minimumFractionDigits:decimals,maximumFractionDigits:decimals}) + suffix;
    if (p<1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}
const io = new IntersectionObserver((entries)=>{
  entries.forEach(e=>{ if(e.isIntersecting){ e.target.classList.add('visible'); io.unobserve(e.target); }});
},{threshold:0.12});
function initObservers() {
  document.querySelectorAll('.reveal').forEach(el=>io.observe(el));
  const cio = new IntersectionObserver((entries)=>{
    entries.forEach(e=>{
      if(e.isIntersecting && !e.target.dataset.done){
        e.target.dataset.done = '1';
        animateCounter(e.target, parseFloat(e.target.dataset.counter),
          parseInt(e.target.dataset.duration||1400),
          e.target.dataset.suffix||'',
          parseInt(e.target.dataset.decimals||0));
        cio.unobserve(e.target);
      }
    });
  },{threshold:0.4});
  document.querySelectorAll('[data-counter]').forEach(el=>cio.observe(el));
  const sections = document.querySelectorAll('[data-section]');
  const nav = document.querySelectorAll('[data-nav]');
  window.addEventListener('scroll', ()=>{
    const y = window.scrollY + 160;
    let current = null;
    sections.forEach(s=>{ if(s.offsetTop <= y) current = s.dataset.section; });
    nav.forEach(n=>{ n.classList.toggle('active', n.dataset.nav===current); });
  });
}
const poll = setInterval(()=>{
  if(document.querySelector('[data-counter]')){ initObservers(); clearInterval(poll); }
},200);
// Re-observe when new reveal elements are injected (modals, product drill-down)
new MutationObserver(()=>{ document.querySelectorAll('.reveal:not(.visible)').forEach(el=>io.observe(el)); })
  .observe(document.body,{childList:true,subtree:true});
</script>
</body>
</html>
'''

# ============================================================
# LAYOUT
# ============================================================
TOP_40 = top_products.head(40).reset_index(drop=True)

app.layout = html.Div([

    # Sticky nav
    html.Div(className='nav', children=[
        html.A('Overview', href='#overview', className='nav-item active', **{'data-nav':'overview'}),
        html.A('Trends', href='#trends', className='nav-item', **{'data-nav':'trends'}),
        html.A('Products', href='#products', className='nav-item', **{'data-nav':'products'}),
        html.A('Compare', href='#compare', className='nav-item', **{'data-nav':'compare'}),
        html.A('Ask AI', href='#ai', className='nav-item', **{'data-nav':'ai'}),
        html.A('Pros & Cons', href='#proscons', className='nav-item', **{'data-nav':'proscons'}),
    ]),

    html.Div(className='app', children=[

        # HERO
        html.Section(id='overview', className='hero', **{'data-section':'overview'}, children=[
            html.Div(className='hero-tag', children=[
                html.Div(className='hero-tag-dot'),
                html.Span('Live · Amazon Electronics'),
            ]),
            html.H1(className='hero-title', children=[
                'What customers ', html.Span('really think', className='accent'), html.Br(),
                'about what they bought.',
            ]),
            html.P(className='hero-sub', children=[
                'A real-time intelligence layer over nearly 100,000 verified customer reviews. Ask questions in plain English. Get answers grounded in what people actually wrote.',
            ]),
            html.Div(className='hero-stats', children=[
                hero_stat('Reviews Indexed', TOTAL_REVIEWS, hint='English · cleaned · deduped'),
                hero_stat('Average Rating', round(AVG_RATING,2), suffix=' ★', decimals=2, hint='Across all products', cls='gold'),
                hero_stat('Positive Share', round(POS_PCT,1), suffix='%', decimals=1, hint=f'{NEG_PCT:.1f}% negative', cls='orange'),
                hero_stat('Unique Products', UNIQUE_PRODUCTS, hint='With full metadata'),
            ]),
            html.Div('Scroll to explore ↓', className='scroll-hint'),
        ]),

        # TRENDS
        html.Section(id='trends', className='section', **{'data-section':'trends'}, children=[
            section_head('01 · Signals', 'Sentiment over time, at a glance.',
                         'How customer mood moves through the years. Smoothed over a 30-day window so you see the shape, not the noise.'),
            html.Div(className='grid grid-2-1 reveal', children=[
                chart_panel(
                    'Sentiment Over Time',
                    '30-day rolling mean of daily review counts',
                    dcc.Graph(id='trend-fig', figure=sentiment_trend_fig('ALL'), config={'displayModeBar': False}),
                    ask_id='ask-trend',
                    extras=html.Div(className='tabs', children=[
                        html.Button('1Y', id='t-1y', className='tab', n_clicks=0),
                        html.Button('5Y', id='t-5y', className='tab', n_clicks=0),
                        html.Button('ALL', id='t-all', className='tab active', n_clicks=0),
                    ]),
                ),
                chart_panel(
                    'Sentiment Mix',
                    'Overall distribution',
                    dcc.Graph(figure=sentiment_donut_fig(), config={'displayModeBar': False}),
                    ask_id='ask-donut',
                ),
            ]),
        ]),

        # PRODUCTS
        html.Section(id='products', className='section', **{'data-section':'products'}, children=[
            section_head('02 · Products', 'Where price meets satisfaction.',
                         'The relationship between what customers pay and how they feel about it. Click any product to drill in.'),
            html.Div(className='grid grid-1-1 reveal', children=[
                chart_panel(
                    'Price vs Rating',
                    'Do expensive products score better?',
                    dcc.Graph(figure=price_bracket_fig(), config={'displayModeBar': False}),
                    ask_id='ask-price',
                ),
                html.Div(className='panel', children=[
                    html.Div(className='panel-head', children=[
                        html.Div([
                            html.Div('Top Products by Review Volume', className='panel-title'),
                            html.Div('Click any product for a deep-dive', className='panel-sub'),
                        ]),
                    ]),
                    dcc.Loading(type='circle', color='#FF9900', children=html.Div(className='product-list', children=[
                        product_row(r, i) for i, (_, r) in enumerate(TOP_40.iterrows())
                    ])),
                ]),
            ]),
        ]),

        # COMPARE
        html.Section(id='compare', className='section', **{'data-section':'compare'}, children=[
            section_head('03 · Head-to-Head', 'Compare any two products.',
                         'Pick two of the top products. The AI reads the reviews on both sides and writes the honest comparison.'),
            html.Div(className='panel reveal', children=[
                html.Div(style={'display':'grid','gridTemplateColumns':'1fr 1fr','gap':'14px','marginBottom':'14px'}, children=[
                    html.Div([
                        html.Div('Product A', className='panel-sub', style={'marginBottom':'6px'}),
                        dcc.Dropdown(
                            id='cmp-a',
                            options=[{'label': t[:70], 'value': t} for t in TOP_40['product_title']],
                            placeholder='Select product A...',
                            className='cmp-dd',
                        ),
                    ]),
                    html.Div([
                        html.Div('Product B', className='panel-sub', style={'marginBottom':'6px'}),
                        dcc.Dropdown(
                            id='cmp-b',
                            options=[{'label': t[:70], 'value': t} for t in TOP_40['product_title']],
                            placeholder='Select product B...',
                            className='cmp-dd',
                        ),
                    ]),
                ]),
                html.Button('Compare', id='cmp-send', n_clicks=0,
                            style={'background':'linear-gradient(135deg,#FF9900,#FFAC33)','color':'#0F1419','border':'none',
                                   'borderRadius':'12px','padding':'12px 22px','fontWeight':'700','fontSize':'13px','cursor':'pointer','marginBottom':'16px'}),
                dcc.Loading(type='dot', color='#FF9900', children=html.Div(id='cmp-output', children=[
                    html.Div(className='empty-state', children=[
                        html.H3('Pick two products'),
                        html.P('Get an AI-generated head-to-head based on what reviewers actually say.'),
                    ]),
                ])),
            ]),
        ]),

        # AI CHAT
        html.Section(id='ai', className='section', **{'data-section':'ai'}, children=[
            section_head('04 · Intelligence', 'Ask anything. Get grounded answers.',
                         'A RAG system over every review. Ask in plain English — get a cited answer with the actual reviews that informed it.'),
            html.Div(className='reveal', children=[
                html.Div(className='chat', children=[
                    html.Div(className='chat-head', children=[
                        html.Div(className='chat-dot'),
                        html.Div([
                            html.Div('Ask Anything', className='chat-title'),
                            html.Div('RAG over 50K reviews · GPT-4o-mini · query rewriting enabled', className='chat-sub'),
                        ]),
                    ]),
                    dcc.Loading(type='dot', color='#FF9900', parent_className='chat-body-wrap', children=html.Div(id='chat-body', className='chat-body', children=[
                        html.Div(className='empty-state', children=[
                            html.H3('What do customers think?'),
                            html.P('Ask a question and I\'ll answer using real reviews as evidence.'),
                        ]),
                    ])),
                    html.Div(className='suggestions', children=[
                        html.Div('Common complaints about battery life?', className='suggestion', id='sug-1', n_clicks=0),
                        html.Div('What do people love about Kindle?', className='suggestion', id='sug-2', n_clicks=0),
                        html.Div('Issues with wireless headphones', className='suggestion', id='sug-3', n_clicks=0),
                    ]),
                    html.Div(className='chat-input', children=[
                        dcc.Input(id='chat-input', type='text', placeholder='Ask anything about these reviews...', debounce=False, n_submit=0),
                        html.Button('Ask', id='chat-send', n_clicks=0),
                    ]),
                    dcc.Store(id='chat-history', data=[]),
                ]),
            ]),
        ]),

        # PROS CONS
        html.Section(id='proscons', className='section', **{'data-section':'proscons'}, children=[
            section_head('05 · Summaries', 'Pros and cons, extracted.',
                         'Type any product or category. The system retrieves the most relevant positive and negative reviews, then distills them.'),
            html.Div(className='panel reveal', children=[
                html.Div(className='panel-head', children=[
                    html.Div([
                        html.Div('Pros & Cons Generator', className='panel-title'),
                        html.Div('AI-extracted from reviews', className='panel-sub'),
                    ]),
                ]),
                html.Div(style={'display':'flex','gap':'8px','marginBottom':'10px'}, children=[
                    dcc.Input(id='pc-input', type='text', placeholder='e.g. wireless earbuds, kindle, smartwatch',
                              style={'flex':'1','background':'#0F1419','border':'1px solid #2A3544','borderRadius':'12px',
                                     'padding':'12px 14px','color':'#E8E8E8','fontFamily':'inherit','fontSize':'13px'},
                              n_submit=0),
                    html.Button('Generate', id='pc-send', n_clicks=0,
                                style={'background':'linear-gradient(135deg,#FF9900,#FFAC33)','color':'#0F1419','border':'none',
                                       'borderRadius':'12px','padding':'0 20px','fontWeight':'700','fontSize':'13px','cursor':'pointer'}),
                ]),
                dcc.Loading(type='dot', color='#FF9900', children=html.Div(id='pc-output', children=[
                    html.Div(className='empty-state', children=[
                        html.H3('Pick any category'),
                        html.P('Get the top 3 pros and top 3 cons, extracted from reviews.'),
                    ]),
                ])),
            ]),
        ]),

        footer(LINKEDIN, GITHUB, EMAIL),
    ]),

    # Modals (Phase 2 + 3)
    modal('product-modal', 'product-modal-body'),
    modal('chart-modal', 'chart-modal-body'),
])

# ============================================================
# CALLBACKS
# ============================================================

# --- Sentiment trend time range ---
@app.callback(
    Output('trend-fig', 'figure'),
    Output('t-1y', 'className'), Output('t-5y', 'className'), Output('t-all', 'className'),
    Input('t-1y', 'n_clicks'), Input('t-5y', 'n_clicks'), Input('t-all', 'n_clicks'),
)
def update_trend(c1, c5, ca):
    trig = ctx.triggered_id or 't-all'
    w = {'t-1y':'1Y','t-5y':'5Y','t-all':'ALL'}[trig]
    return (
        sentiment_trend_fig(w),
        'tab active' if trig=='t-1y' else 'tab',
        'tab active' if trig=='t-5y' else 'tab',
        'tab active' if trig=='t-all' else 'tab',
    )

# --- Chat ---
@app.callback(
    Output('chat-body', 'children'),
    Output('chat-history', 'data'),
    Output('chat-input', 'value'),
    Input('chat-send', 'n_clicks'),
    Input('chat-input', 'n_submit'),
    Input('sug-1', 'n_clicks'), Input('sug-2', 'n_clicks'), Input('sug-3', 'n_clicks'),
    State('chat-input', 'value'),
    State('chat-history', 'data'),
    prevent_initial_call=True
)
def handle_chat(send_c, submit_c, s1, s2, s3, input_val, history):
    trig = ctx.triggered_id
    sug_map = {
        'sug-1': 'What are common complaints about battery life?',
        'sug-2': 'What do people love about Kindle?',
        'sug-3': 'What are issues with wireless headphones?',
    }
    q = sug_map[trig] if trig in sug_map else (input_val or '').strip()
    if not q:
        return no_update, no_update, no_update

    try:
        answer, hits = run_rag(q, k=8)
        sources = hits[['product_title','rating','text']].head(3).to_dict('records') if len(hits) else []
    except Exception as e:
        answer = f"⚠️ Couldn't get a response right now. ({str(e)[:80]})"
        sources = []

    history = (history or []) + [{'q': q, 'a': answer, 'sources': sources}]
    history = history[-5:]

    body = []
    for turn in history:
        body.append(html.Div(className='msg msg-user', children=html.Div(turn['q'], className='bubble')))
        ai_children = [dcc.Markdown(turn['a'], className='bubble bubble-md')]
        for s in turn['sources']:
            full_text = s['text']
            preview = full_text[:220] + ('…' if len(full_text)>220 else '')
            ai_children.append(html.Details(className='source-card', children=[
                html.Summary(className='source-head', children=[
                    html.Div(s['product_title'][:60], className='source-product'),
                    html.Div(f"{s['rating']}/5 ★", className='source-rating'),
                ]),
                html.Div(preview, className='source-preview'),
                html.Div(full_text, className='source-full'),
            ]))
        body.append(html.Div(className='msg msg-ai', children=ai_children))
    return body, history, ''


# --- Pros/Cons ---
@app.callback(
    Output('pc-output', 'children'),
    Input('pc-send', 'n_clicks'),
    Input('pc-input', 'n_submit'),
    State('pc-input', 'value'),
    prevent_initial_call=True
)
def handle_proscons(c, s, val):
    q = (val or '').strip()
    if not q:
        return no_update

    plan = rewrite_query(f"pros and cons of {q}")
    queries = plan.get('search_queries') or [q]
    product_hint = plan.get('product_hint') or q

    cand = retrieve(queries, k=200)
    if product_hint:
        mask = cand['product_title'].str.contains(product_hint, case=False, na=False)
        if mask.sum() >= 20:
            cand = cand[mask]

    pos = cand[cand['sentiment']=='pos'].head(25)
    neg = cand[cand['sentiment']=='neg'].head(25)

    if len(pos) < 3 or len(neg) < 3:
        return html.Div(className='empty-state', children=[html.P(f'Not enough reviews for "{q}". Try a broader term.')])

    try:
        pros_lines, cons_lines = generate_pros_cons(q, pos, neg)
    except Exception as e:
        return html.Div(f'Error: {str(e)[:100]}', className='empty-state')

    pros_items = [html.Div(p, className='pc-item') for p in pros_lines] if pros_lines else [html.Div('—', className='pc-item')]
    cons_items = [html.Div(c, className='pc-item') for c in cons_lines] if cons_lines else [html.Div('—', className='pc-item')]

    return html.Div(className='proscons-grid', children=[
        html.Div(className='pc-col pos', children=[
            html.Div('★ Pros', className='pc-head pos'),
            *pros_items,
        ]),
        html.Div(className='pc-col neg', children=[
            html.Div('⚠ Cons', className='pc-head neg'),
            *cons_items,
        ]),
    ])


# --- PHASE 2: product drill-down modal ---
@app.callback(
    Output('product-modal', 'className'),
    Output('product-modal-body', 'children'),
    Input({'type':'product-click','index':ALL}, 'n_clicks'),
    Input('product-modal-close', 'n_clicks'),
    prevent_initial_call=True
)
def open_product_modal(product_clicks, close_c):
    trig = ctx.triggered_id
    if trig == 'product-modal-close' or not any(product_clicks or []):
        return 'modal-overlay hidden', no_update

    # find which product was clicked
    idx = trig.get('index') if isinstance(trig, dict) else None
    if idx is None:
        raise PreventUpdate
    row = TOP_40.iloc[idx]
    title = row['product_title']

    # filter reviews for that product
    sub = df_emb[df_emb['product_title']==title]

    # stats
    n = len(sub)
    avg = sub['rating'].mean()
    pos_pct = (sub['sentiment']=='pos').mean() * 100
    neg_pct = (sub['sentiment']=='neg').mean() * 100

    # pros/cons (best-effort)
    pos_sample = sub[sub['sentiment']=='pos'].head(15)
    neg_sample = sub[sub['sentiment']=='neg'].head(15)
    pros_items, cons_items = [], []
    if len(pos_sample) >= 3 and len(neg_sample) >= 3:
        try:
            pros_lines, cons_lines = generate_pros_cons(title, pos_sample, neg_sample)
            pros_items = [html.Div(p, className='pc-item') for p in pros_lines]
            cons_items = [html.Div(c, className='pc-item') for c in cons_lines]
        except Exception:
            pass

    # example reviews
    top_pos = sub[sub['sentiment']=='pos'].head(3)
    top_neg = sub[sub['sentiment']=='neg'].head(3)

    def review_card(r, klass):
        return html.Div(className=f'modal-review {klass}', children=[
            html.Div(className='modal-review-head', children=[
                html.Span(f"{r['rating']}/5 ★", style={'color':'#F5C518','fontWeight':'600'}),
                html.Span(str(r['date'])[:10] if 'date' in r else ''),
            ]),
            html.Div(r['text'][:400] + ('...' if len(r['text'])>400 else '')),
        ])

    # get image for this product
    img_row = df_emb[df_emb['product_title']==title].iloc[0]
    img_url = img_row.get('image_url') if 'image_url' in img_row.index else None

    head_children = []
    if img_url and isinstance(img_url, str):
        head_children.append(html.Img(src=img_url, className='modal-hero-img'))
    head_children.append(html.Div([
        html.Div(title, className='modal-title'),
        html.Div(f"{n:,} reviews analyzed", className='modal-sub'),
    ], style={'flex':'1'}))

    body = [
        html.Div(className='modal-hero', children=head_children),

        html.Div(className='modal-stats', children=[
            html.Div(className='modal-stat', children=[
                html.Div('Reviews', className='modal-stat-label'),
                html.Div(f"{n:,}", className='modal-stat-value'),
            ]),
            html.Div(className='modal-stat', children=[
                html.Div('Avg Rating', className='modal-stat-label'),
                html.Div(f"{avg:.2f} ★", className='modal-stat-value gold'),
            ]),
            html.Div(className='modal-stat', children=[
                html.Div('Positive', className='modal-stat-label'),
                html.Div(f"{pos_pct:.0f}%", className='modal-stat-value orange'),
            ]),
            html.Div(className='modal-stat', children=[
                html.Div('Negative', className='modal-stat-label'),
                html.Div(f"{neg_pct:.0f}%", className='modal-stat-value'),
            ]),
        ]),

        html.Div('Sentiment Over Time', className='modal-section-title'),
        dcc.Graph(figure=product_trend_fig(title), config={'displayModeBar': False}),
    ]

    if pros_items and cons_items:
        body.extend([
            html.Div('AI Summary', className='modal-section-title'),
            html.Div(className='proscons-grid', children=[
                html.Div(className='pc-col pos', children=[
                    html.Div('★ Pros', className='pc-head pos'),
                    *pros_items,
                ]),
                html.Div(className='pc-col neg', children=[
                    html.Div('⚠ Cons', className='pc-head neg'),
                    *cons_items,
                ]),
            ]),
        ])

    if len(top_pos):
        body.append(html.Div('Top Positive Reviews', className='modal-section-title'))
        body.extend([review_card(r, 'pos') for _, r in top_pos.iterrows()])
    if len(top_neg):
        body.append(html.Div('Top Negative Reviews', className='modal-section-title'))
        body.extend([review_card(r, 'neg') for _, r in top_neg.iterrows()])

    return 'modal-overlay', body


# --- PHASE 3a: "Ask about this chart" modal ---
@app.callback(
    Output('chart-modal', 'className'),
    Output('chart-modal-body', 'children'),
    Input('ask-trend', 'n_clicks'),
    Input('ask-donut', 'n_clicks'),
    Input('ask-price', 'n_clicks'),
    Input('chart-modal-close', 'n_clicks'),
    prevent_initial_call=True
)
def open_chart_modal(t, d, p, close_c):
    trig = ctx.triggered_id
    if trig == 'chart-modal-close' or trig is None:
        return 'modal-overlay hidden', no_update

    if trig == 'ask-trend':
        chart_name = 'Sentiment Over Time'
        context = f"Positive share: {POS_PCT:.1f}%, Negative share: {NEG_PCT:.1f}%, Total reviews: {TOTAL_REVIEWS:,}. The chart shows 30-day rolling mean of daily review volumes by sentiment, spanning ~15 years."
    elif trig == 'ask-donut':
        chart_name = 'Sentiment Mix'
        context = f"Positive: {POS_PCT:.1f}%, Negative: {NEG_PCT:.1f}%, Neutral: {100-POS_PCT-NEG_PCT:.1f}%. Total reviews: {TOTAL_REVIEWS:,}."
    elif trig == 'ask-price':
        chart_name = 'Price vs Rating'
        rows = "\n".join([f"- {r['bracket']}: avg rating {r['avg_rating']:.2f}, {r['review_count']:,} reviews" for _, r in brackets.iterrows()])
        context = f"Price brackets and their average ratings:\n{rows}"
    else:
        raise PreventUpdate

    try:
        answer = summarize_chart(chart_name, context)
    except Exception as e:
        answer = f"Couldn't analyze: {str(e)[:100]}"

    body = [
        html.Div(chart_name, className='modal-title'),
        html.Div('AI-generated insight', className='modal-sub'),
        html.Div(className='msg-ai', children=[
            dcc.Markdown(answer, className='bubble bubble-md'),
        ]),
    ]
    return 'modal-overlay', body


# --- PHASE 3b: Product comparison ---
@app.callback(
    Output('cmp-output', 'children'),
    Input('cmp-send', 'n_clicks'),
    State('cmp-a', 'value'),
    State('cmp-b', 'value'),
    prevent_initial_call=True
)
def handle_compare(n, a, b):
    if not a or not b:
        return html.Div(className='empty-state', children=[html.P('Pick two products first.')])
    if a == b:
        return html.Div(className='empty-state', children=[html.P('Pick two different products.')])

    try:
        result = compare_products(a, b)
    except Exception as e:
        return html.Div(f'Error: {str(e)[:100]}', className='empty-state')

    # parse the structured output into sections
    import re
    sections = {'a_wins': [], 'b_wins': [], 'verdict': ''}
    current = None
    for line in result.splitlines():
        raw = line.strip()
        if not raw: continue
        # strip markdown wrappers and inline asterisks around section headers
        header_check = re.sub(r'[*:]+', '', raw).strip().lower()
        if 'where a wins' in header_check: current = 'a_wins'; continue
        if 'where b wins' in header_check: current = 'b_wins'; continue
        if header_check.startswith('verdict') or 'verdict' == header_check:
            current = 'verdict'
            # capture any text on same line after "Verdict:"
            inline = re.sub(r'^\s*\**\s*verdict\s*:?\s*\**\s*', '', raw, flags=re.IGNORECASE).strip()
            if inline:
                sections['verdict'] = inline
            continue
        # strip leading numbering/bullets + wrapping ** but keep inline **bold**
        cleaned = re.sub(r'^\s*[\d*\-.)\s]+', '', raw).strip()
        if current == 'verdict':
            sections['verdict'] += (' ' if sections['verdict'] else '') + cleaned
        elif current and cleaned:
            sections[current].append(cleaned)

    def get_img(product_title):
        sub = df_emb[df_emb['product_title']==product_title]
        if len(sub) == 0: return None
        url = sub.iloc[0].get('image_url') if 'image_url' in sub.columns else None
        return url if isinstance(url, str) else None

    def wins_col(label, product, items, accent_class):
        img_url = get_img(product)
        header_children = []
        if img_url:
            header_children.append(html.Img(src=img_url, className='cmp-product-img'))
        header_children.append(html.Div([
            html.Div(label, className='cmp-col-label'),
            html.Div(product[:60], className='cmp-col-product'),
        ], style={'flex':'1'}))

        return html.Div(className=f'cmp-col {accent_class}', children=[
            html.Div(className='cmp-col-header', children=header_children),
            html.Div(className='cmp-items', children=[
                html.Div(className='cmp-item', children=[
                    html.Div(className='cmp-item-num', children=str(i+1)),
                    dcc.Markdown(item, className='cmp-item-text'),
                ]) for i, item in enumerate(items)
            ]) if items else html.Div('—', className='cmp-item-text'),
        ])

    return html.Div(className='cmp-result', children=[
        html.Div(className='cmp-grid', children=[
            wins_col('Where A Wins', a, sections['a_wins'], 'a'),
            wins_col('Where B Wins', b, sections['b_wins'], 'b'),
        ]),
        html.Div(className='cmp-verdict', children=[
            html.Div('VERDICT', className='cmp-verdict-label'),
            dcc.Markdown(sections['verdict'] or 'No verdict provided.', className='cmp-verdict-text'),
        ]) if sections['verdict'] else None,
    ])


if __name__ == '__main__':
    app.run(debug=True, port=8050)