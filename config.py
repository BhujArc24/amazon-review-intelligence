COLORS = {
    'bg':'#0F1419','panel':'#161D26','panel_hi':'#1E2733','border':'#2A3544',
    'text':'#E8E8E8','text_dim':'#8B95A3',
    'orange':'#FF9900','orange_hi':'#FFAC33','gold':'#F5C518',
    'pos':'#00A862','neg':'#E63946','neu':'#6B7785',
}

PLOTLY_LAYOUT = dict(
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family='Inter, system-ui, sans-serif', color=COLORS['text'], size=12),
    xaxis=dict(gridcolor=COLORS['border'], zerolinecolor=COLORS['border']),
    yaxis=dict(gridcolor=COLORS['border'], zerolinecolor=COLORS['border']),
    margin=dict(l=40, r=20, t=40, b=40),
    hoverlabel=dict(bgcolor=COLORS['panel_hi'], bordercolor=COLORS['orange'], font_size=12),
)

DATA_DIR = 'data'
OPENAI_MODEL = 'gpt-4o-mini'

LINKEDIN = 'https://www.linkedin.com/in/archit-bhujang-840b63217/'
GITHUB = 'https://github.com/BhujArc24'
EMAIL = 'bhujang.archit@gmail.com'