import pandas as pd
import plotly.graph_objects as go
from config import COLORS, PLOTLY_LAYOUT
from data_loader import daily, brackets, POS_PCT, NEG_PCT, df_emb


def sentiment_trend_fig(window='ALL'):
    d = daily.copy().sort_values('date')
    if window == '1Y':
        d = d[d['date'] >= d['date'].max() - pd.Timedelta(days=365)]
    elif window == '5Y':
        d = d[d['date'] >= d['date'].max() - pd.Timedelta(days=365*5)]
    d = d.set_index('date').sort_index()
    d = d[['pos','neu','neg']].rolling('30D').mean().reset_index()

    fig = go.Figure()
    for name, col_data, color, fillc in [
        ('Positive', d['pos'], COLORS['pos'], 'rgba(0,168,98,0.15)'),
        ('Neutral', d['neu'], COLORS['neu'], 'rgba(107,119,133,0.1)'),
        ('Negative', d['neg'], COLORS['neg'], 'rgba(230,57,70,0.15)'),
    ]:
        fig.add_trace(go.Scatter(
            x=d['date'], y=col_data, name=name, mode='lines',
            line=dict(color=color, width=2),
            fill='tozeroy', fillcolor=fillc,
            hovertemplate='%{x|%b %Y}<br>%{y:.1f} avg/day<extra>'+name+'</extra>'
        ))
    fig.update_layout(**PLOTLY_LAYOUT,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        hovermode='x unified', height=360)
    return fig


def price_bracket_fig():
    b = brackets.copy()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=b['bracket'], y=b['review_count'], name='Reviews',
        marker_color=COLORS['orange'], opacity=0.75, yaxis='y2',
        hovertemplate='%{x}<br>%{y:,} reviews<extra></extra>'))
    fig.add_trace(go.Scatter(x=b['bracket'], y=b['avg_rating'], name='Avg Rating',
        mode='lines+markers', line=dict(color=COLORS['gold'], width=3),
        marker=dict(size=11, color=COLORS['gold'], line=dict(color='#fff', width=1)),
        hovertemplate='%{x}<br>%{y:.2f} ★<extra></extra>'))
    layout = {k:v for k,v in PLOTLY_LAYOUT.items() if k != 'yaxis'}
    fig.update_layout(**layout, height=360,
        yaxis=dict(title='Avg Rating', range=[0,5], gridcolor=COLORS['border']),
        yaxis2=dict(title='Review Count', overlaying='y', side='right', gridcolor='rgba(0,0,0,0)'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1))
    return fig


def sentiment_donut_fig():
    vals = [POS_PCT, NEG_PCT, 100-POS_PCT-NEG_PCT]
    fig = go.Figure(go.Pie(
        labels=['Positive','Negative','Neutral'], values=vals, hole=0.72,
        marker=dict(colors=[COLORS['pos'], COLORS['neg'], COLORS['neu']], line=dict(color=COLORS['bg'], width=2)),
        textinfo='none', hovertemplate='%{label}<br>%{value:.1f}%<extra></extra>'))
    layout = {k:v for k,v in PLOTLY_LAYOUT.items() if k not in ['xaxis','yaxis']}
    fig.update_layout(**layout, height=360, showlegend=False,
        annotations=[
            dict(text=f'{POS_PCT:.0f}%', x=0.5, y=0.56, font=dict(size=36, color=COLORS['orange']), showarrow=False),
            dict(text='POSITIVE', x=0.5, y=0.42, font=dict(size=11, color=COLORS['text_dim']), showarrow=False),
        ])
    return fig


def product_trend_fig(product_title):
    """Mini trend chart for a single product (used in drill-down modal)."""
    sub = df_emb[df_emb['product_title']==product_title].copy()
    if len(sub) < 5:
        return go.Figure().update_layout(**PLOTLY_LAYOUT, height=220,
            annotations=[dict(text='Not enough data', x=0.5, y=0.5, showarrow=False, font=dict(color=COLORS['text_dim']))])
    sub['date'] = pd.to_datetime(sub['date'])
    daily_p = sub.groupby([sub['date'].dt.to_period('M'), 'sentiment']).size().unstack(fill_value=0)
    daily_p.index = daily_p.index.to_timestamp()
    daily_p = daily_p.reset_index()
    for c in ['pos','neg','neu']:
        if c not in daily_p.columns: daily_p[c] = 0

    fig = go.Figure()
    for name, col, color in [('Positive','pos',COLORS['pos']), ('Neutral','neu',COLORS['neu']), ('Negative','neg',COLORS['neg'])]:
        fig.add_trace(go.Scatter(x=daily_p['date'], y=daily_p[col], name=name, mode='lines',
            line=dict(color=color, width=2), stackgroup='one'))
    fig.update_layout(**PLOTLY_LAYOUT, height=220, showlegend=False, hovermode='x unified')
    return fig