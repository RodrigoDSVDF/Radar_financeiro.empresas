"""Normalização auditável de movimentações financeiras."""
import io
import math
import re
import unicodedata
from datetime import datetime
import pandas as pd

FIELDS = {
    'data': ['data', 'dia', 'dt', 'data movimento', 'data lancamento', 'dt lancamento', 'date', 'movimento'],
    'descricao': ['descricao', 'historico', 'detalhes', 'observacao', 'memo', 'estabelecimento', 'favorecido', 'lancamento'],
    'valor': ['valor', 'montante', 'total', 'amount', 'valor r$', 'valor liquido'],
    'tipo': ['tipo', 'operacao', 'natureza', 'credito debito', 'debito credito', 'entrada saida'],
    'entrada': ['entrada', 'entradas', 'credito', 'creditos', 'recebimento', 'recebimentos'],
    'saida': ['saida', 'saidas', 'debito', 'debitos', 'pagamento', 'pagamentos'],
    'categoria': ['categoria', 'grupo', 'classificacao', 'centro de custo'],
}

def clean_name(v):
    s = unicodedata.normalize('NFKD', str(v)).encode('ascii', 'ignore').decode().lower().strip()
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()

def guess_mapping(df):
    result = {}
    used = set()
    for field, aliases in FIELDS.items():
        candidates = []
        for col in df.columns:
            norm = clean_name(col)
            if norm in aliases:
                candidates.append((0, col))
            elif any(norm.startswith(a + ' ') or norm.endswith(' ' + a) for a in aliases if len(a)>3):
                candidates.append((1, col))
        for _, col in sorted(candidates, key=lambda v:v[0]):
            if col not in used:
                result[field] = col
                used.add(col)
                break
    return result

def parse_money(v):
    if pd.isna(v) or str(v).strip() in ('', '-', '—'): return None
    if isinstance(v, (int, float)) and not isinstance(v, bool): return float(v) if math.isfinite(float(v)) else None
    s = str(v).strip().replace('R$', '').replace('\u00a0','').replace(' ', '')
    negative = s.startswith('(') and s.endswith(')')
    s = s.strip('()').replace('+','')
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.') if s.rfind(',') > s.rfind('.') else s.replace(',', '')
    elif ',' in s:
        s = s.replace('.', '').replace(',', '.')
    elif s.count('.') > 1:
        s = s.replace('.', '')
    try:
        x = float(s)
        if not math.isfinite(x): return None
        return -x if negative else x
    except ValueError: return None

def parse_dates(series, dayfirst=True):
    return pd.to_datetime(series, errors='coerce', dayfirst=dayfirst)

def detect_type(raw, value):
    s = clean_name(raw)
    if any(t in s.split() for t in ['credito', 'entrada', 'receita', 'recebimento', 'credit', 'c']): return 'Receita'
    if any(t in s.split() for t in ['debito', 'saida', 'despesa', 'pagamento', 'debit', 'd']): return 'Despesa'
    return None

def categorize(description):
    s = clean_name(description)
    groups = {
        'Aluguel': ['aluguel', 'locacao'],
        'Pessoal': ['salario', 'folha', 'funcionario', 'pro labore'],
        'Fornecedores': ['fornecedor', 'mercadoria', 'insumo', 'compra estoque'],
        'Impostos': ['imposto', 'tributo', 'das mei', 'simples nacional', 'darf'],
        'Serviços': ['internet', 'energia', 'agua', 'telefone', 'software', 'assinatura'],
        'Vendas': ['venda', 'cliente', 'recebimento', 'maquininha'],
        'Transferências': ['transferencia', 'aplicacao', 'resgate', 'entre contas'],
        'Empréstimos': ['emprestimo', 'financiamento'],
    }
    for group, terms in groups.items():
        if any(term in s for term in terms): return group
    return 'Não categorizado'

def normalize(df, mapping, dayfirst=True, source='Arquivo'):
    if not mapping.get('data') or not (mapping.get('valor') or mapping.get('entrada') or mapping.get('saida')):
        raise ValueError('Mapeie uma coluna de data e uma coluna de valor ou entrada/saída.')
    out = pd.DataFrame(index=df.index)
    out['data'] = parse_dates(df[mapping['data']], dayfirst)
    out['descricao'] = df[mapping['descricao']].fillna('').astype(str) if mapping.get('descricao') else 'Sem descrição'
    if mapping.get('entrada') or mapping.get('saida'):
        def amounts(field):
            if not mapping.get(field):
                return pd.Series(0.0,index=df.index), pd.Series(False,index=df.index)
            original = df[mapping[field]]
            parsed = original.map(parse_money)
            blank = original.isna() | original.astype(str).str.strip().isin(['', '-', '—'])
            invalid = parsed.isna() & ~blank
            return parsed.fillna(0), invalid
        inc, inc_invalid = amounts('entrada')
        exp, exp_invalid = amounts('saida')
        # Dois campos representam magnitudes; preserva transações separadas caso ambos estejam preenchidos.
        both = (inc.abs()>0)&(exp.abs()>0)
        if both.any(): raise ValueError(f'{int(both.sum())} linhas têm entrada e saída simultaneamente; revise a planilha.')
        out['valor_assinado'] = inc.abs() - exp.abs()
        invalid_value = ((inc==0)&(exp==0)) | inc_invalid | exp_invalid
    else:
        values = df[mapping['valor']].map(parse_money)
        invalid_value = values.isna()
        if mapping.get('tipo'):
            types = [detect_type(t, v if pd.notna(v) else 0) for t,v in zip(df[mapping['tipo']],values)]
            out['valor_assinado'] = [abs(v) * (1 if t=='Receita' else -1) if pd.notna(v) and t is not None else float('nan') for v,t in zip(values,types)]
        else: out['valor_assinado'] = values
    out['categoria'] = df[mapping['categoria']].fillna('').astype(str) if mapping.get('categoria') else out['descricao'].map(categorize)
    out['categoria'] = out['categoria'].replace('', 'Não categorizado')
    out['fonte'] = source
    valid = out['data'].notna() & out['valor_assinado'].notna() & ~invalid_value & (out['valor_assinado'] != 0)
    rejected = df.loc[~valid].copy()
    out = out.loc[valid].copy()
    out['tipo'] = out['valor_assinado'].map(lambda x: 'Receita' if x>0 else 'Despesa')
    out['valor'] = out['valor_assinado'].abs()
    out['mes'] = out['data'].dt.to_period('M').astype(str)
    out['possivel_duplicidade'] = out.duplicated(subset=['data','descricao','valor_assinado'],keep=False)
    return out.reset_index(drop=True), rejected

def read_file(upload):
    data = upload.getvalue()
    name = upload.name.lower()
    if len(data) > 15*1024*1024: raise ValueError('Arquivo maior que 15 MB.')
    if name.endswith('.csv'):
        last = None
        for encoding in ('utf-8-sig','latin-1'):
            for sep in (None, ';', ','):
                try:
                    d = pd.read_csv(io.BytesIO(data),encoding=encoding,sep=sep,engine='python')
                    if len(d.columns)>1: return {'CSV':d}
                except Exception as e: last=e
        raise ValueError(f'CSV não reconhecido: {last}')
    if name.endswith('.xlsx'):
        return pd.read_excel(io.BytesIO(data),sheet_name=None,engine='openpyxl')
    if name.endswith('.ofx'):
        from ofxparse import OfxParser
        ofx = OfxParser.parse(io.BytesIO(data))
        rows = [{'Data':t.date,'Descrição':t.payee or t.memo or 'Movimentação','Valor':float(t.amount)} for t in ofx.account.statement.transactions]
        return {'OFX':pd.DataFrame(rows)}
    raise ValueError('Formato não suportado. Use CSV, XLSX ou OFX.')

def stats(df):
    income = df.loc[df.tipo=='Receita','valor'].sum()
    expense = df.loc[df.tipo=='Despesa','valor'].sum()
    return income, expense, income-expense
