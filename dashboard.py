"""Visualizações e agregações determinísticas, independentes da interface."""
from html import escape
import pandas as pd
import plotly.graph_objects as go
from engine import stats, normalize

GREEN='#39D9A8'; RED='#FF8394'; BLUE='#6CA8FF'; MUTED='#9AACC2'; GOLD='#F6C76B'
PALETTE=[GREEN,BLUE,'#AA9BFF',GOLD,'#58C9E7','#FF8394','#88C48E','#D8A0D7','#7794B3','#A1B4C8']

def money(value):
    return ('- ' if value<0 else '')+'R$ '+f'{abs(value):,.2f}'.replace(',','X').replace('.',',').replace('X','.')

def pct(value): return f'{value:.1f}%'.replace('.',',')

def demo_data():
    rows=[]
    for month in range(5,11):
        scale=1+(month-5)*.045
        for day in range(2,29,2):
            rows.append((f'{day:02d}/{month:02d}/2026','Venda balcão' if day%4==0 else 'Venda PIX',round((900+(day*137+month*71)%900)*scale,2),'Vendas'))
        for day,desc,value,cat in [(3,'Aluguel',2800,'Aluguel'),(5,'Folha de pagamento',4200,'Pessoal'),(7,'Fornecedor A',3100,'Fornecedores'),(12,'Energia e internet',640,'Serviços'),(17,'Fornecedor B',2400,'Fornecedores'),(20,'Impostos',910,'Impostos'),(25,'Marketing',420,'Marketing'),(27,'Taxas de cartão',310,'Taxas')]:
            rows.append((f'{day:02d}/{month:02d}/2026',desc,-round(value*(1+(month-5)*.018),2),cat))
    raw=pd.DataFrame(rows,columns=['Data','Descrição','Valor','Categoria'])
    data,_=normalize(raw,{'data':'Data','descricao':'Descrição','valor':'Valor','categoria':'Categoria'},source='Demonstração fictícia')
    return raw,data

def monthly(df):
    index=pd.period_range(df.data.min().to_period('M'),df.data.max().to_period('M'),freq='M').astype(str)
    p=df.groupby(['mes','tipo']).valor.sum().unstack(fill_value=0).reindex(index,fill_value=0)
    p=p.reindex(columns=['Receita','Despesa'],fill_value=0).fillna(0)
    p['Saldo']=p.Receita-p.Despesa
    p['Acumulado']=p.Saldo.cumsum()
    return p

def daily(df):
    p=df.assign(dia=df.data.dt.normalize()).groupby('dia').valor_assinado.sum().sort_index()
    return p.reindex(pd.date_range(p.index.min(),p.index.max(),freq='D'),fill_value=0)

def category_totals(df,kind='Despesa'):
    return df.loc[df.tipo.eq(kind)].groupby('categoria').valor.sum().sort_values(ascending=False)

def layout(fig,height=340,legend=False):
    fig.update_layout(template='plotly_dark',height=height,paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font=dict(family='Arial, sans-serif',size=12,color=MUTED),margin=dict(l=8,r=14,t=16,b=12),showlegend=legend,legend=dict(orientation='h',y=1.12,x=0,font=dict(size=11)),hoverlabel=dict(bgcolor='#202f40',font_color='#f0f6ff'),separators=',.')
    fig.update_xaxes(showgrid=False,zeroline=False,automargin=True)
    fig.update_yaxes(gridcolor='#253449',zerolinecolor='#3a4b5d',automargin=True,tickprefix='R$ ')
    return fig

def bars(df):
    p=monthly(df); fig=go.Figure()
    for k,name,color in [('Receita','Recebimentos',GREEN),('Despesa','Pagamentos',RED)]:
        fig.add_bar(x=p.index,y=p[k],name=name,marker_color=color,hovertemplate='%{x}<br>R$ %{y:,.2f}<extra>'+name+'</extra>')
    fig.update_layout(barmode='group',bargap=.32)
    return layout(fig,350,True)

def donut(df,kind='Despesa'):
    s=category_totals(df,kind)
    if s.empty: return None
    if len(s)>8: s=pd.concat([s.iloc[:7],pd.Series([s.iloc[7:].sum()],index=['Demais categorias'])])
    fig=go.Figure(go.Pie(labels=s.index,values=s.values,hole=.73,sort=False,marker=dict(colors=PALETTE,line=dict(color='#111b28',width=3)),textinfo='none',hovertemplate='%{label}<br>R$ %{value:,.2f}<br>%{percent}<extra></extra>'))
    fig.add_annotation(text=f'<b>{money(s.sum())}</b><br><span style="font-size:11px">Total</span>',x=.5,y=.5,showarrow=False,font=dict(size=15,color='#e8eef7'))
    return layout(fig,310,False)

def accumulated(df):
    p=daily(df).cumsum(); fig=go.Figure(go.Scatter(x=p.index,y=p.values,mode='lines',line=dict(color=BLUE,width=2.8),fill='tozeroy',fillcolor='rgba(108,168,255,.13)',hovertemplate='%{x|%d/%m/%Y}<br>R$ %{y:,.2f}<extra>Acumulado</extra>'))
    fig.add_hline(y=0,line_dash='dot',line_color='#68798a')
    return layout(fig,330)

def balance_bars(df):
    p=monthly(df); fig=go.Figure(go.Bar(x=p.index,y=p.Saldo,marker_color=[GREEN if v>=0 else RED for v in p.Saldo],hovertemplate='%{x}<br>R$ %{y:,.2f}<extra>Saldo</extra>'))
    return layout(fig,320)

def waterfall(df):
    inc,exp,bal=stats(df)
    fig=go.Figure(go.Waterfall(x=['Recebimentos','Pagamentos','Saldo'],measure=['relative','relative','total'],y=[inc,-exp,0],increasing=dict(marker=dict(color=GREEN)),decreasing=dict(marker=dict(color=RED)),totals=dict(marker=dict(color=BLUE)),connector=dict(line=dict(color='#5c7188',dash='dot')),hovertemplate='%{x}<br>R$ %{y:,.2f}<extra></extra>'))
    return layout(fig,320)

def ranking(df,kind='Despesa'):
    s=category_totals(df,kind).head(12).sort_values()
    if s.empty:return None
    fig=go.Figure(go.Bar(x=s.values,y=s.index,orientation='h',marker=dict(color=RED if kind=='Despesa' else GREEN),hovertemplate='%{y}<br>R$ %{x:,.2f}<extra></extra>'))
    layout(fig,max(290,38*len(s)+45));fig.update_yaxes(tickprefix='',showgrid=False,zeroline=False);fig.update_xaxes(tickprefix='R$ ',gridcolor='#253449',showgrid=True)
    return fig

def expense_trend(df):
    cats=category_totals(df).head(6).index
    if not len(cats): return None
    x=monthly(df).index; fig=go.Figure()
    e=df[df.tipo.eq('Despesa')]
    for i,cat in enumerate(cats):
        s=e[e.categoria.eq(cat)].groupby('mes').valor.sum().reindex(x,fill_value=0)
        fig.add_scatter(x=x,y=s.values,name=escape(str(cat)),mode='lines+markers',line=dict(color=PALETTE[i],width=2),hovertemplate='%{x}<br>R$ %{y:,.2f}<extra>%{fullData.name}</extra>')
    return layout(fig,350,True)

def heatmap(df):
    d=df[df.tipo.eq('Despesa')].copy()
    if d.empty:return None
    d['weekday']=d.data.dt.dayofweek; d['week']=((d.data.dt.day-1)//7+1)
    p=d.groupby(['weekday','week']).valor.sum().unstack(fill_value=0).reindex(index=range(7),columns=range(1,6),fill_value=0).fillna(0)
    fig=go.Figure(go.Heatmap(z=p.values,x=['1–7','8–14','15–21','22–28','29–31'],y=['Seg','Ter','Qua','Qui','Sex','Sáb','Dom'],colorscale=[[0,'#162334'],[.4,'#235B66'],[1,GREEN]],hovertemplate='%{y} · dias %{x}<br>R$ %{z:,.2f}<extra></extra>',colorbar=dict(tickprefix='R$ ',thickness=10)))
    layout(fig,320);fig.update_yaxes(tickprefix='',autorange='reversed',showgrid=False)
    return fig
