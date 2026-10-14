"""Lê os anexos do RREO emitidos mensalmente no Elotech (xlsx). Uso: python3 ler_rreo_elotech.py <pasta de um mês>"""
import sys, os, glob, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ler_rgf_elotech import linhas, achar
def arq(pasta, k): g = glob.glob(os.path.join(pasta, '*Anexo_%s_*' % k)); return g[0] if g else None
def ler(pasta):
    L14, meta = linhas(arq(pasta, 'XIV'))
    b = {'mde': achar(L14, 'Mínimo Anual de <18% / 25%>'), 'mde_min': achar(L14, 'Mínimo Anual de <18% / 25%>', 1), 'mde_p': achar(L14, 'Mínimo Anual de <18% / 25%>', 2),
         'fundeb': achar(L14, 'Mínimo Anual de 70% do FUNDEB'), 'fundeb_min': achar(L14, 'Mínimo Anual de 70% do FUNDEB', 1), 'fundeb_p': achar(L14, 'Mínimo Anual de 70% do FUNDEB', 2),
         'asps': achar(L14, 'Despesas com Ações e Serviços Públicos de Saúde executadas'), 'asps_min': achar(L14, 'Despesas com Ações e Serviços Públicos de Saúde executadas', 1), 'asps_p': achar(L14, 'Despesas com Ações e Serviços Públicos de Saúde executadas', 2),
         'oc_rec': achar(L14, 'Receita de Operação de Crédito'), 'oc_rec_sal': achar(L14, 'Receita de Operação de Crédito', 1), 'dcap': achar(L14, 'Despesa de Capital Líquida'), 'dcap_sal': achar(L14, 'Despesa de Capital Líquida', 1),
         'rcl': achar(L14, 'Receita Corrente Líquida'),
         'prim_meta': achar(L14, 'Resultado Primário - Acima da Linha'), 'prim': achar(L14, 'Resultado Primário - Acima da Linha', 1),
         'nom_meta': achar(L14, 'Resultado Nominal - Acima da Linha'), 'nom': achar(L14, 'Resultado Nominal - Acima da Linha', 1)}
    if arq(pasta, 'VI'):
        L6, _ = linhas(arq(pasta, 'VI'))
        b.update({'prim_abaixo': achar(L6, 'RESULTADO PRIMÁRIO (SEM RPPS) - Abaixo da Linha'), 'nom_abaixo': achar(L6, 'RESULTADO NOMINAL (SEM RPPS) AJUSTADO'),
                  'rec_prim': achar(L6, 'RECEITA PRIMÁRIA TOTAL (EXCETO FONTES RPPS)', 1), 'desp_prim_emp': achar(L6, 'DESPESA PRIMÁRIA TOTAL (EXCETO FONTES RPPS)', 1)})
    if arq(pasta, 'VIII'):
        L8, _ = linhas(arq(pasta, 'VIII'))
        b.update({'mde_rec_imp': achar(L8, '3- TOTAL DA RECEITA RESULTANTE DE IMPOSTOS', 1), 'mde_exigido': achar(L8, '29- APLICAÇÃO EM MDE'), 'mde_canc_rp': achar(L8, '27- (-) CANCELAMENTO'),
                  'fundeb_rec': achar(L8, '6- TOTAL DAS RECEITAS DO FUNDEB', 1), 'fundeb_naoapl_p': achar(L8, '18- TOTAL DA RECEITA RECEBIDA E NÃO APLICADA', 4)})
    if arq(pasta, 'XII'):
        L12, _ = linhas(arq(pasta, 'XII'))
        b.update({'asps_rec': achar(L12, 'TOTAL DAS RECEITAS RESULTANTES DE IMPOSTOS', 2), 'asps_emp': achar(L12, 'TOTAL (XI)', 2), 'asps_emp_p': achar(L12, 'PERCENTUAL DA RECEITA DE IMPOSTOS'), 'saude_total_liq': achar(L12, 'TOTAL DAS DESPESAS COM SAÚDE (XLVII)', 4)})
    return {'meta': meta, 'b': b}
if __name__ == '__main__':
    r = ler(sys.argv[1]); print(r['meta']); [print(k, v) for k, v in r['b'].items()]
