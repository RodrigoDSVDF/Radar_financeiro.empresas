import unittest
import pandas as pd
from engine import normalize, guess_mapping, stats, read_file
from dashboard import (demo_data, monthly, daily, bars, donut, accumulated, balance_bars, waterfall, ranking, expense_trend, heatmap)
from reports import report_pdf
import io

class Upload(io.BytesIO):
    name='test.csv'

class RadarTests(unittest.TestCase):
    def test_signed(self):
        d=pd.DataFrame({'Data':['10/11/2026','11/11/2026'],'Descrição':['Venda','Aluguel'],'Valor':['1.500,00','-800,00']})
        out,bad=normalize(d,guess_mapping(d)); self.assertEqual(len(bad),0); self.assertEqual(stats(out),(1500,800,700))
    def test_types(self):
        d=pd.DataFrame({'Dia':['10/11/2026']*3,'Histórico':['A','B','C'],'Montante':[2000,650,100],'Operação':['Crédito','Débito','desconhecido']})
        out,bad=normalize(d,guess_mapping(d)); self.assertEqual(stats(out),(2000,650,1350)); self.assertEqual(len(bad),1)
    def test_separate(self):
        d=pd.DataFrame({'Data':['10/11/2026']*3,'Entrada':[900,None,100],'Saída':[None,300,'erro']})
        out,bad=normalize(d,guess_mapping(d)); self.assertEqual(stats(out),(900,300,600));self.assertEqual(len(bad),1)
    def test_csv(self):
        d=read_file(Upload('Data;Valor\n10/11/2026;2.500,00\n'.encode()))['CSV'];out,bad=normalize(d,guess_mapping(d));self.assertEqual(stats(out),(2500,0,2500))
    def test_demo_charts_report(self):
        raw,d=demo_data();self.assertEqual(len(raw),132);self.assertAlmostEqual(monthly(d).Saldo.sum(),stats(d)[2]);self.assertAlmostEqual(daily(d).sum(),stats(d)[2])
        for f in [bars,donut,accumulated,balance_bars,waterfall,ranking,expense_trend,heatmap]: self.assertTrue(f(d).to_json())
        self.assertTrue(report_pdf(d).startswith(b'%PDF'))
    def test_income_only(self):
        _,d=demo_data();d=d[d.tipo.eq('Receita')];self.assertIsNone(donut(d));self.assertIsNone(heatmap(d));self.assertTrue(bars(d).to_json())

if __name__=='__main__': unittest.main()
