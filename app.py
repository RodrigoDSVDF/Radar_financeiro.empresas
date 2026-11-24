"""Radar Financeiro Business — interface Streamlit."""
from pathlib import Path
from html import escape
import hashlib
import pandas as pd
import streamlit as st
from engine import read_file, guess_mapping, normalize, stats
from dashboard import (GREEN, RED, BLUE, GOLD, PALETTE, money, pct, demo_data, monthly,
                       category_totals, bars, donut, accumulated, balance_bars, waterfall,
                       ranking, expense_trend, heatmap)
from reports import report_pdf

st.set_page_config(page_title='Radar Financeiro Business',page_icon='◈',layout='wide',initial_sidebar_state='expanded')
st.markdown('<style>'+Path(__file__).with_name('assets').joinpath('style.css').read_text(encoding='utf-8')+'</style>',unsafe_allow_html=True)

def html(content): st.markdown(content,unsafe_allow_html=True)
def card(label,value,note,color):
    html(f'<div class="rf-kpi" style="--accent:{color}"><div class="rf-kpi-label">{escape(label)}</div><div class="rf-kpi-value">{escape(value)}</div><div class="rf-kpi-note">{escape(note)}</div></div>')
def section(title,subtitle=''):
    html(f'<div class="rf-section"><h2>{escape(title)}</h2><span>{escape(subtitle)}</span></div>')
def chart(title,desc,fig,key):
    with st.container(border=True):
        html(f'<div class="rf-chart-title">{escape(title)}</div><div class="rf-chart-sub">{escape(desc)}</div>')
        if fig is None: st.info('Sem dados suficientes para este gráfico.')
        else: st.plotly_chart(fig,use_container_width=True,key=key,config={'displaylogo':False,'scrollZoom':False,'modeBarButtonsToRemove':['lasso2d','select2d']})
def insight(title,desc,color=GREEN):
    html(f'<div class="rf-insight" style="--accent:{color}"><strong>{escape(title)}</strong><p>{escape(desc)}</p></div>')
def legend(s):
    if len(s)>8: s=pd.concat([s.iloc[:7],pd.Series([s.iloc[7:].sum()],index=['Demais categorias'])])
    for i,(cat,v) in enumerate(s.items()):
        html(f'<div style="display:flex;justify-content:space-between;gap:8px;font-size:12px;margin:5px 0"><span style="color:#aebed1"><span style="color:{PALETTE[i]}">●</span> {escape(str(cat))}</span><strong>{pct(v/s.sum()*100)}</strong></div>')

raw_demo,demo=demo_data()
with st.sidebar:
    html('<div class="rf-brand"><div class="rf-logo">◈</div><div><strong>Radar Financeiro</strong><small>Business intelligence</small></div></div>')
    st.markdown('**Fonte dos dados**')
    mode=st.radio('Modo de análise',['Demonstração','Meus arquivos'],label_visibility='collapsed',help='Os dados fictícios nunca são misturados aos arquivos enviados.')
    uploads=[]
    dayfirst=True
    if mode=='Meus arquivos':
        uploads=st.file_uploader('Importar movimentações',type=['csv','xlsx','ofx'],accept_multiple_files=True,help='Até 15 MB por arquivo. Use a aba Importação para conferir o mapeamento.')
        dayfirst=st.toggle('Datas brasileiras (dia/mês)',value=True)
        st.caption('Selecione a aba Importação para revisar colunas e confirmar cada arquivo.')
    else:
        st.caption('Explore um negócio fictício com seis meses de movimentações.')
        st.download_button('Baixar CSV de exemplo',raw_demo.to_csv(index=False,sep=';',decimal=',').encode('utf-8-sig'),'radar_exemplo.csv','text/csv',use_container_width=True)
    st.divider()
    st.caption('RADAR BUSINESS · V2\n\nAnálises calculadas localmente pelo motor Python, sem API de IA. Não há conexão bancária.')

is_demo=mode=='Demonstração'
html(f'''<div class="rf-hero"><div class="rf-hero-inner"><div class="rf-eyebrow">Radar / Inteligência financeira</div><h1>Clareza para cada decisão.</h1><p>Transforme movimentações em uma visão gerencial de recebimentos, pagamentos, composição de gastos e evolução do caixa.</p><span class="rf-status {'demo' if is_demo else ''}">{'DADOS FICTÍCIOS · DEMONSTRAÇÃO' if is_demo else 'MODO DE IMPORTAÇÃO · SEUS ARQUIVOS'}</span></div></div>''')
# Explicit mapping confirmation: changing any mapping invalidates approval until reconfirmed.
def import_data():
    parts=[]; rejected_parts=[]; pending=0
    if not uploads:
        st.info('Envie CSV, XLSX ou OFX pela barra lateral para começar.')
        return parts,rejected_parts,pending
    st.caption('Cada arquivo/aba só participa do painel após a confirmação do mapeamento. Alterações exigem nova confirmação.')
    for idx,upload in enumerate(uploads):
        key=hashlib.sha256(upload.getvalue()).hexdigest()[:12]
        base=f'{idx}_{key}'
        try: sheets=read_file(upload)
        except Exception as e:
            st.error(f'{upload.name}: {e}');pending+=1;continue
        with st.expander(f'{upload.name} · {len(sheets)} aba(s)',expanded=True):
            sheet_name=st.selectbox('Aba ou tabela',list(sheets),key=f'sheet_{base}')
            raw=sheets[sheet_name].copy()
            if raw.empty:
                st.warning('Aba sem dados.');pending+=1;continue
            st.caption(f'{len(raw)} linhas · {len(raw.columns)} colunas')
            st.dataframe(raw.head(8),hide_index=True,use_container_width=True)
            # Column labels converted into unique strings to support numeric Excel headers.
            raw.columns=[str(c) for c in raw.columns]
            if not raw.columns.is_unique:
                st.error('Existem cabeçalhos duplicados. Renomeie as colunas no arquivo.');pending+=1;continue
            guess=guess_mapping(raw); cols=[None]+list(raw.columns)
            names={'data':'Data','descricao':'Descrição','valor':'Valor único (com sinal ou tipo)','tipo':'Tipo (crédito/débito)','entrada':'Entrada / crédito','saida':'Saída / débito','categoria':'Categoria'}
            chosen={}; left,right=st.columns(2)
            for i,(field,label) in enumerate(names.items()):
                with (left if i%2==0 else right):
                    chosen[field]=st.selectbox(label,cols,index=cols.index(guess[field]) if field in guess else 0,format_func=lambda c:'Não utilizar' if c is None else c,key=f'{base}_{sheet_name}_{field}')
            selected=[v for v in chosen.values() if v is not None]
            if len(selected)!=len(set(selected)):
                st.error('Use cada coluna em apenas um campo.');pending+=1;continue
            if chosen['valor'] and (chosen['entrada'] or chosen['saida']):
                st.warning('Foram escolhidos valor único e entrada/saída. Remova um dos formatos para evitar ambiguidade.');pending+=1;continue
            if chosen['valor'] and not chosen['tipo']:
                st.caption('Sem coluna de tipo, valores positivos são recebimentos e negativos são pagamentos.')
            try: normalized,rejected=normalize(raw,chosen,dayfirst,upload.name+' / '+str(sheet_name))
            except Exception as e:
                st.error(f'Não foi possível processar: {e}');pending+=1;continue
            st.caption(f'{len(normalized)} movimentações válidas · {len(rejected)} linhas não importadas')
            if len(rejected):
                st.warning('Revise as linhas não importadas antes de confirmar.')
                st.dataframe(rejected.head(20),use_container_width=True,hide_index=True)
                st.download_button('Baixar linhas não importadas',rejected.to_csv(index=False,sep=';').encode('utf-8-sig'),f'rejeitadas_{idx}.csv','text/csv',key=f'rej_{base}')
            if normalized.empty:
                pending+=1;continue
            st.dataframe(normalized[['data','descricao','tipo','valor','categoria']].head(5),use_container_width=True,hide_index=True)
            token=hashlib.sha256(repr((chosen,dayfirst,str(sheet_name),upload.name)).encode()).hexdigest()
            approval=f'approved_{base}_{sheet_name}'
            if st.button('Confirmar mapeamento',key=f'confirm_{base}_{sheet_name}',type='primary'):
                st.session_state[approval]=token
            if st.session_state.get(approval)==token:
                st.success('Mapeamento confirmado. Dados disponíveis no painel.')
                parts.append(normalized)
                if len(rejected): rejected_parts.append(rejected)
            else:
                st.info('Aguardando confirmação do mapeamento.');pending+=1
    return parts,rejected_parts,pending

# Tabs remain clearly visible; import is processed before drawing analysis.
tabs=st.tabs(['Visão geral','Fluxo de caixa','Despesas e receitas','Movimentações','Importação e qualidade'])
with tabs[4]:
    section('Importação e qualidade','Validação de dados')
    if is_demo:
        st.info('Você está no modo demonstração. Selecione Meus arquivos na barra lateral para importar dados reais.')
        parts=[demo]; rejected_parts=[]; pending=0
        st.dataframe(raw_demo.head(12),hide_index=True,use_container_width=True)
    else:
        parts,rejected_parts,pending=import_data()
    rejected_count=sum(map(len,rejected_parts))
    st.caption('A ferramenta é voltada a planilhas de movimentações; DRE, estoque e contas por competência exigem outros módulos.')

if not parts or not any(len(p) for p in parts):
    for tab in tabs[:4]:
        with tab: st.info('Importe e confirme ao menos um arquivo válido na aba Importação e qualidade para visualizar o painel.')
    st.stop()
data=pd.concat(parts,ignore_index=True)
data['possivel_duplicidade']=data.duplicated(subset=['data','descricao','valor_assinado'],keep=False)
with st.sidebar:
    st.divider();st.markdown('**Filtros do painel**')
    signature=hashlib.sha256(pd.util.hash_pandas_object(data[['data','descricao','valor_assinado','categoria','fonte']],index=True).values.tobytes()).hexdigest()[:16]
    minimum=data.data.min().date();maximum=data.data.max().date()
    dates=st.date_input('Período',value=(minimum,maximum),min_value=minimum,max_value=maximum,key=f'dates_{signature}')
    cats=sorted(data.categoria.unique());sources=sorted(data.fonte.unique())
    selected_cats=st.multiselect('Categorias',cats,default=cats,key=f'cats_{signature}')
    selected_sources=st.multiselect('Fontes',sources,default=sources,key=f'sources_{signature}')
    types=st.multiselect('Tipo de movimentação',['Receita','Despesa'],default=['Receita','Despesa'],key=f'types_{signature}')
filtered=data[data.categoria.isin(selected_cats)&data.fonte.isin(selected_sources)&data.tipo.isin(types)].copy()
if isinstance(dates,(tuple,list)) and len(dates)==2:
    filtered=filtered[filtered.data.dt.date.between(*dates)].copy()
else:
    for tab in tabs[:4]:
        with tab: st.info('Selecione as duas datas para aplicar o período.')
    st.stop()
if filtered.empty:
    for tab in tabs[:4]:
        with tab: st.warning('Não há movimentações nos filtros selecionados.')
    st.stop()
inc,exp,bal=stats(filtered); ratio=exp/inc*100 if inc else None
expenses=category_totals(filtered); duplicates=int(filtered.possivel_duplicidade.sum())
if pending:
    st.warning(f'{pending} arquivo(s) ainda não confirmado(s) ou inválido(s). O painel inclui somente dados confirmados.')
with tabs[0]:
    section('Visão executiva',f'{dates[0]:%d/%m/%Y} — {dates[1]:%d/%m/%Y}')
    a,b,c,d=st.columns(4)
    with a: card('Recebimentos',money(inc),'Total de entradas no filtro',GREEN)
    with b: card('Pagamentos',money(exp),'Total de saídas no filtro',RED)
    with c: card('Saldo das movimentações',money(bal),'Entradas menos saídas',GREEN if bal>=0 else RED)
    with d: card('Comprometimento de caixa',pct(ratio) if ratio is not None else '—','Pagamentos / recebimentos',GOLD if ratio is not None and ratio>=90 else BLUE)
    st.caption('Saldo de movimentações não é lucro contábil nem saldo bancário. Aportes, empréstimos e transferências podem afetar os totais.')
    left,right=st.columns([1.55,1])
    with left: chart('Recebimentos × pagamentos','Comparação mensal das movimentações',bars(filtered),'overview_bars')
    with right:
        with st.container(border=True):
            html('<div class="rf-chart-title">Composição das despesas</div><div class="rf-chart-sub">Participação de cada categoria nas saídas</div>')
            fig=donut(filtered)
            if fig is not None:
                st.plotly_chart(fig,use_container_width=True,key='overview_donut',config={'displayModeBar':False});legend(expenses)
            else: st.info('Sem despesas no período.')
    left,right=st.columns([1.55,1])
    with left: chart('Evolução acumulada','Movimentações líquidas acumuladas desde a primeira data selecionada',accumulated(filtered),'overview_acc')
    with right:
        with st.container(border=True):
            html('<div class="rf-chart-title">Diagnóstico do período</div><div class="rf-chart-sub">Indicadores e alertas calculados pelas regras do sistema</div>')
            insight('Saldo positivo' if bal>=0 else 'Saldo negativo',f'Entradas menos saídas: {money(bal)}.',GREEN if bal>=0 else RED)
            if not expenses.empty:
                insight('Maior categoria de despesa',f'{expenses.index[0]}: {money(expenses.iloc[0])} ({pct(expenses.iloc[0]/exp*100)} das saídas).',BLUE)
            if ratio is not None and ratio>=90: insight('Atenção ao comprometimento',f'Os pagamentos equivalem a {pct(ratio)} dos recebimentos.',GOLD)
            if not inc: insight('Sem recebimentos','Não é possível calcular a relação entre pagamentos e recebimentos.',GOLD)
            if duplicates: insight('Possíveis duplicidades',f'{duplicates} lançamentos sinalizados. Confira antes de excluir.',GOLD)
            if rejected_count: insight('Linhas não importadas',f'{rejected_count} linhas de fontes confirmadas exigem revisão.',GOLD)
with tabs[1]:
    section('Fluxo de caixa','Movimentações líquidas')
    st.caption('A linha acumulada começa em zero; não inclui saldo de abertura. Meses sem lançamentos no intervalo entre registros aparecem com zero.')
    chart('Saldo acumulado por dia','Acompanhe a trajetória das entradas menos as saídas',accumulated(filtered),'flow_acc')
    a,b=st.columns(2)
    with a: chart('Resultado mensal de caixa','Verde: saldo positivo · rosa: saldo negativo',balance_bars(filtered),'flow_month')
    with b: chart('Ponte de movimentações','Como os recebimentos e pagamentos formam o saldo do período',waterfall(filtered),'flow_waterfall')
    st.dataframe(monthly(filtered).rename_axis('Mês').reset_index(),hide_index=True,use_container_width=True,column_config={k:st.column_config.NumberColumn(k,format='R$ %.2f') for k in ['Receita','Despesa','Saldo','Acumulado']})
with tabs[2]:
    section('Despesas e receitas','Composição por categoria')
    a,b=st.columns(2)
    with a: chart('Ranking de despesas','As 12 categorias com maior volume de pagamentos',ranking(filtered),'expense_rank')
    with b: chart('Ranking de recebimentos','As 12 categorias com maior volume de entradas',ranking(filtered,'Receita'),'income_rank')
    chart('Evolução das principais despesas','Até seis categorias com maior total de saídas',expense_trend(filtered),'expense_trend')
    chart('Mapa de intensidade dos pagamentos','Total por dia da semana e faixa de dias do mês, agregado no período',heatmap(filtered),'expense_heatmap')
    st.caption('Categorias são importadas ou sugeridas por palavras-chave. Transferências e empréstimos não são excluídos automaticamente.')
with tabs[3]:
    section('Movimentações detalhadas',f'{len(filtered)} lançamentos')
    query=st.text_input('Pesquisar descrição, categoria ou fonte',placeholder='Ex.: fornecedor, aluguel, venda...')
    only_duplicates=st.checkbox('Exibir apenas possíveis duplicidades')
    view=filtered.copy()
    if query.strip():
        mask=pd.Series(False,index=view.index)
        for col in ['descricao','categoria','fonte']:mask|=view[col].str.contains(query,case=False,regex=False,na=False)
        view=view[mask]
    if only_duplicates:view=view[view.possivel_duplicidade]
    st.dataframe(view[['data','descricao','tipo','categoria','valor','fonte','possivel_duplicidade']].sort_values('data',ascending=False),hide_index=True,use_container_width=True,column_config={'data':st.column_config.DateColumn('Data',format='DD/MM/YYYY'),'descricao':'Descrição','tipo':'Tipo','categoria':'Categoria','valor':st.column_config.NumberColumn('Valor',format='R$ %.2f'),'fonte':'Fonte','possivel_duplicidade':'Possível duplicidade'})
    st.caption('Os downloads utilizam todos os filtros da barra lateral, não a pesquisa local da tabela.')
    a,b=st.columns(2)
    with a:st.download_button('Exportar CSV padronizado',filtered.to_csv(index=False,sep=';',decimal=',').encode('utf-8-sig'),'movimentacoes_padronizadas.csv','text/csv',use_container_width=True)
    with b:st.download_button('Exportar relatório PDF',report_pdf(filtered),'relatorio_radar_financeiro.pdf','application/pdf',use_container_width=True)
with tabs[4]:
    section('Conferência do painel','Dados confirmados')
    insight('Movimentações válidas',f'{len(data)} lançamentos no conjunto de dados; {len(filtered)} nos filtros atuais.')
    insight('Possíveis duplicidades',f'{int(data.possivel_duplicidade.sum())} lançamentos sinalizados por data, descrição e valor iguais; nenhuma exclusão automática.',GOLD)
    insight('Linhas rejeitadas',f'{rejected_count} linhas não importadas nas fontes confirmadas.',GOLD if rejected_count else GREEN)
st.caption('Radar Financeiro Business V2 · Ferramenta gerencial. Valide as informações antes de decidir. Não há autenticação ou armazenamento persistente nesta versão.')
