import io
from engine import stats
from dashboard import money

def report_pdf(df):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    buffer=io.BytesIO(); doc=SimpleDocTemplate(buffer)
    styles=getSampleStyleSheet(); inc,exp,bal=stats(df)
    items=[Paragraph('Radar Financeiro Business - Relatório',styles['Title']),Spacer(1,14),
           Paragraph(f'Recebimentos: {money(inc)}',styles['Normal']),Paragraph(f'Pagamentos: {money(exp)}',styles['Normal']),
           Paragraph(f'Saldo do período: {money(bal)}',styles['Normal']),Spacer(1,14)]
    cat=df.groupby(['tipo','categoria'])['valor'].sum().reset_index().sort_values('valor',ascending=False)
    rows=[['Tipo','Categoria','Valor']]+[[str(r.tipo),str(r.categoria),money(r.valor)] for r in cat.itertuples()]
    table=Table(rows,repeatRows=1,colWidths=[90,260,130]);table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#17334a')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#eef4f7')]),('BOTTOMPADDING',(0,0),(-1,-1),8)]));items.append(table)
    items += [Spacer(1,16),Paragraph('Nota: movimentação de caixa não representa necessariamente lucro contábil. Verifique transferências, empréstimos, impostos e lançamentos.',styles['Normal'])]
    doc.build(items);return buffer.getvalue()

