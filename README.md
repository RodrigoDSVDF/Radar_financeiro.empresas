# Radar Financeiro Business · V2

Aplicação Streamlit para análise gerencial de movimentações financeiras. A nova interface usa HTML/CSS personalizado, tema escuro e gráficos Plotly interativos. Não requer chave de API.

## Executar no Windows / VS Code

Abra o terminal na pasta que contém `app.py`:

```powershell
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
streamlit run app.py
```

No macOS/Linux, use `python3 -m venv .venv` e `source .venv/bin/activate`.

## Publicar no Streamlit Community Cloud

1. Extraia o ZIP. Envie **o conteúdo da pasta interna inteira** para o GitHub (incluindo `assets/` e `.streamlit/`).
2. Abra https://share.streamlit.io/ e selecione o repositório e a branch.
3. Defina `app.py` como arquivo principal. Não é necessário configurar secrets.

## Como utilizar

- O app abre com 132 transações fictícias de seis meses. O modo demonstração está sinalizado e não se mistura com arquivos reais.
- Na lateral, escolha **Meus arquivos**, envie CSV, XLSX ou OFX, e entre na aba **Importação e qualidade**.
- Selecione uma aba por arquivo Excel, confira a prévia e confirme as colunas. Utilize valor único (sinal ou tipo) OU campos separados de entrada/saída.
- Clique em **Confirmar mapeamento**. Alterações de colunas ou formato de data exigem nova confirmação.
- Use filtros de período, categoria, fonte e tipo. Navegue pelas abas do painel.
- Na aba Movimentações, exporte a tabela filtrada em CSV ou o relatório em PDF. A pesquisa local da tabela não altera os downloads.

## Gráficos e indicadores

- KPIs: recebimentos, pagamentos, saldo de movimentações e relação pagamentos/recebimentos.
- Comparação mensal, gráfico de rosca com legenda de categorias, curva acumulada diária.
- Saldo mensal, cascata de entradas/saídas, ranking de receitas/despesas, evolução das principais categorias e mapa de intensidade de pagamentos.
- Alertas de possíveis duplicidades, saldo negativo, comprometimento elevado e linhas rejeitadas.

## Estrutura

- `app.py`: interface, navegação e fluxo de importação.
- `assets/style.css`: identidade visual, componentes HTML e adaptação para telas menores.
- `.streamlit/config.toml`: tema e limite de upload.
- `engine.py`: leitura, mapeamento, normalização e cálculos.
- `dashboard.py`: agregações, dados demonstrativos e gráficos Plotly.
- `reports.py`: relatório PDF.
- `test_radar.py`: testes do motor e dos gráficos (`python -m unittest -v`).

## Limitações

- É um analisador de movimentações, não uma ferramenta universal para DRE, estoque ou contabilidade por competência. Cabeçalhos deslocados devem ser reorganizados antes da importação. Uma aba por arquivo é selecionada a cada vez.
- A classificação de categorias por descrição é heurística. Transferências, aportes e empréstimos não são excluídos automaticamente. Recebimentos menos pagamentos não são lucro contábil ou saldo bancário; o acumulado começa em zero.
- Duplicidades são sinalizadas, não excluídas. Revise as linhas rejeitadas e o mapeamento; tipos desconhecidos na coluna de operação não são presumidos como receita.
- Não há autenticação, cobrança ou banco de dados persistente. Antes de publicar para clientes com dados reais, implemente controle de acesso, isolamento, proteção e política de retenção de dados. Não envie dados sensíveis a uma implantação pública sem esses controles.
- Os testes automatizados não substituem uma verificação da interface em navegador.
