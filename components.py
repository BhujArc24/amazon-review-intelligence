from dash import html, dcc
from config import COLORS


def hero_stat(label, value, suffix='', decimals=0, hint='', cls=''):
    return html.Div([
        html.Div(label, className='hero-stat-label'),
        html.Div('0', className=f'hero-stat-value {cls}',
                 **{'data-counter': str(value), 'data-suffix': suffix, 'data-decimals': str(decimals)}),
        html.Div(hint, className='hero-stat-hint'),
    ])


def section_head(kicker, title, sub):
    return html.Div(className='section-head reveal', children=[
        html.Div(className='section-title-group', children=[
            html.Div(kicker, className='section-kicker'),
            html.Div(title, className='section-title'),
            html.Div(sub, className='section-sub'),
        ]),
    ])


def product_row(r, idx):
    pos = r['pos_pct']; neg = r['neg_pct']; neu = 1-pos-neg
    img_url = r.get('image_url') if hasattr(r, 'get') else r['image_url'] if 'image_url' in r.index else None

    img_el = html.Img(src=img_url, className='product-thumb') if img_url and isinstance(img_url, str) else \
             html.Div('📦', className='product-thumb product-thumb-fallback')

    return html.Div(
        className='product-row',
        id={'type':'product-click','index':idx},
        n_clicks=0,
        children=[
            img_el,
            html.Div(className='product-info', children=[
                html.Div(r['product_title'][:80], className='product-name'),
                html.Div([
                    html.Span(f"{int(r['review_count'])} reviews"),
                    html.Span('•'),
                    html.Span(f"{pos*100:.0f}% positive"),
                ], className='product-meta'),
                html.Div(className='sent-bar', children=[
                    html.Div(style={'flex': pos, 'background': COLORS['pos']}),
                    html.Div(style={'flex': neu, 'background': COLORS['neu']}),
                    html.Div(style={'flex': neg, 'background': COLORS['neg']}),
                ]),
            ]),
            html.Div(f"{r['avg_rating']:.1f} ★", className='product-rating'),
        ])


def chart_panel(title, subtitle, graph_component, ask_id=None, extras=None):
    """Panel wrapper with optional 'Ask AI about this chart' button (Phase 3)."""
    head_right = []
    if extras:
        head_right.append(extras)
    if ask_id:
        head_right.append(html.Button('Ask AI about this',
            id=ask_id, n_clicks=0, className='ask-chart-btn'))

    return html.Div(className='panel', children=[
        html.Div(className='panel-head', children=[
            html.Div([
                html.Div(title, className='panel-title'),
                html.Div(subtitle, className='panel-sub'),
            ]),
            html.Div(style={'display':'flex','gap':'10px','alignItems':'center'}, children=head_right) if head_right else None,
        ]),
        graph_component,
    ])


def modal(modal_id, body_id):
    """Generic modal scaffolding. Content filled in by callback."""
    return html.Div(id=modal_id, className='modal-overlay hidden', n_clicks=0, children=[
        html.Div(className='modal-content', children=[
            html.Button('×', id=f'{modal_id}-close', className='modal-close', n_clicks=0),
            html.Div(id=body_id, className='modal-body'),
        ])
    ])


def footer(linkedin, github, email):
    return html.Div(className='foot', children=[
        html.Div('Built with Dash · Plotly · FAISS · OpenAI · Sentence-Transformers', style={'marginBottom':'14px'}),
        html.Div(className='foot-links', children=[
            html.A('LinkedIn', href=linkedin, target='_blank', className='foot-link'),
            html.A('GitHub', href=github, target='_blank', className='foot-link'),
            html.A('Email', href=f'mailto:{email}', className='foot-link'),
        ]),
        html.Div('© Archit Bhujang · 2026', style={'marginTop':'18px','fontSize':'11px','color':'#5A6472'}),
    ])