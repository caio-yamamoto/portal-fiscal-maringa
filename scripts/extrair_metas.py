"""Gera metas.json a partir do RREO Anexo 6 (Resultados Primário e Nominal) publicado no Siconfi.
Uso: python3 extrair_metas.py <pasta com subpastas por ano> metas.json"""
import sys, os, re, glob, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lim_load import load
raiz, saida = sys.argv[1], sys.argv[2]
def vals(v, n): return [(x if isinstance(x, float) else 0.0) for x in (v + [None]*n)[:n]]
def get(rows, pre, n=1):
    for l, v in rows:
        if l.startswith(pre) and any(isinstance(x, float) for x in v): return vals(v, n)
    for l, v in rows:
        if l.startswith(pre): return vals(v, n)
    return [0.0]*n
REC = [('rc','RECEITAS CORRENTES (EXCETO FONTES RPPS)',0),('imp','Impostos, Taxas e Contribuições de Melhoria',1),('iptu','IPTU',2),('iss','ISS',2),('itbi','ITBI',2),('irrf','IRRF',2),('oimp','Outros Impostos',2),
       ('contr','Contribuições',1),('pat','Receita Patrimonial',1),('aplic','Aplicações Financeiras',2),('opat','Outras Receitas Patrimoniais',2),('tc','Transferências Correntes',1),('fpm','Cota-Parte do FPM',2),('icms','Cota-Parte do ICMS',2),
       ('ipva','Cota-Parte do IPVA',2),('itr','Cota-Parte do ITR',2),('lc61','Transferências da LC',2),('fundeb','Transferências do FUNDEB',2),('otc','Outras Transferências Correntes',2),('drc','Demais Receitas Correntes',1),
       ('rpc','RECEITAS PRIMÁRIAS CORRENTES (EXCETO',0),('rk','RECEITAS DE CAPITAL (EXCETO',0),('opc','Operações de Crédito',1),('alien','Alienação de Bens',1),('tk','Transferências de Capital',1),('conv','Convênios',2),('otk','Outras Transferências de Capital',2),('ork','Outras Receitas de Capital',1),
       ('rpk','RECEITAS PRIMÁRIAS DE CAPITAL (EXCETO',0),('rpt','RECEITA PRIMÁRIA TOTAL (EXCETO',0),('rpt_rpps','RECEITA PRIMÁRIA TOTAL (XVI)',0)]
DES = [('dc','DESPESAS CORRENTES (EXCETO FONTES RPPS)',0),('pes','Pessoal e Encargos Sociais',1),('jur','Juros e Encargos da Dívida',1),('odc','Outras Despesas Correntes',1),('dpc','DESPESAS PRIMÁRIAS CORRENTES (EXCETO',0),
       ('dk','DESPESAS DE CAPITAL (EXCETO',0),('inv','Investimentos',1),('invf','Inversões Financeiras',1),('amort','Amortização da Dívida',1),('dpk','DESPESAS PRIMÁRIAS DE CAPITAL (EXCETO',0),('res','RESERVA DE CONTINGÊNCIA',0),
       ('dpt','DESPESA PRIMÁRIA TOTAL (EXCETO',0),('dpt_rpps','DESPESA PRIMÁRIA TOTAL (XXXII)',0)]
out = {'anos': {}}
for pasta in sorted(glob.glob(os.path.join(raiz, '20??'))):
    ano = os.path.basename(pasta); A = {'bims': [], 'b': {}}
    for f in sorted(glob.glob(os.path.join(pasta, '*RREO*BIMESTRAL_*.xls'))):
        b = int(re.search(r'BIMESTRAL_(\d)', f).group(1)); G = load(f); m = G['_meta']
        assert m['Exercício'] == ano and m['Período'].startswith('%dº' % b), (f, m)
        S = G['RREO-Anexo 06']; R = S['Cálculo Acima da Linha - Receitas Primárias']; D = S['Cálculo Acima da Linha - Despesas Primárias']
        ab = S['Cálculo Abaixo da Linha - Resultado Nominal']; aj = S.get('Ajuste Metodológico', [])
        d = {'rec': {k: get(R, p, 2) for k, p, nv in REC}, 'des': {k: get(D, p, 7) for k, p, nv in DES},
             'prim_rpps': get(S['Resultado Primário - Acima da Linha'], 'RESULTADO PRIMÁRIO (COM RPPS)')[0], 'prim': get(S['Resultado Primário - Acima da Linha'], 'RESULTADO PRIMÁRIO (SEM RPPS)')[0],
             'meta_prim': get(S['Meta Fiscal para o Resultado Primário'], 'Meta fixada')[0],
             'jur_at': get(S['Juros Nominais'], 'Juros, Encargos e Variações Monetárias Ativos')[0], 'jur_pas': get(S['Juros Nominais'], 'Juros, Encargos e Variações Monetárias Passivos')[0],
             'nom': get(S['Resultado Nominal - Acima da Linha'], 'RESULTADO NOMINAL')[0], 'meta_nom': get(S['Meta Fiscal para o Resultado Nominal'], 'Meta fixada')[0],
             'dc': get(ab, 'DÍVIDA CONSOLIDADA (', 2), 'ded': get(ab, 'DEDUÇÕES', 2), 'caixa': get(ab, 'Disponibilidade de Caixa Bruta', 2), 'rpp': get(ab, '(-) Restos a Pagar Processados', 2), 'dep': get(ab, '(-) Depósitos', 2), 'dcl': get(ab, 'DÍVIDA CONSOLIDADA LÍQUIDA', 2),
             'nom_ab': get(S['Resultado Nominal - Abaixo da Linha'], 'RESULTADO NOMINAL')[0],
             'aj_rpp': get(aj, 'VARIAÇÃO DO SALDO DE RPP')[0], 'aj_camb': get(aj, 'VARIAÇÃO CAMBIAL')[0], 'nom_ab_aj': get(aj, 'RESULTADO NOMINAL (SEM RPPS) AJUSTADO')[0],
             'prim_ab': get(S.get('Resultado Primário - Abaixo da Linha', []), 'RESULTADO PRIMÁRIO')[0],
             'sup': get(S.get('Informações Adicionais', []), 'Superávit Financeiro')[0]}
        notas = [x for l, v in S.get('Notas Explicativas', []) for x in v if isinstance(x, str) and len(x) > 40]
        if notas: d['nota'] = re.sub(r'\s+', ' ', notas[0]).strip()
        # conferências: primário acima da linha = receita primária realizada - (pagas + RPP pagos + RPNP pagos)
        dp = d['des']['dpt']; calc = d['rec']['rpt'][1] - (dp[3] + dp[4] + dp[6])
        assert abs(calc - d['prim']) < 1, (f, 'primário', calc, d['prim'])
        assert abs(d['prim'] + d['jur_at'] - d['jur_pas'] - d['nom']) < 1, (f, 'nominal')
        A['b'][b] = d; A['bims'].append(b)
        print(ano, 'B%d' % b, 'primário %.0f meta %.0f | nominal %.0f meta %.0f | abaixo %.0f' % (d['prim'], d['meta_prim'], d['nom'], d['meta_nom'], d['nom_ab']))
    out['anos'][ano] = A
json.dump(out, open(saida, 'w'), ensure_ascii=False, separators=(',', ':'))
print('gravado', saida, os.path.getsize(saida))
