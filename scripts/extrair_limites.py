"""Gera limites.json a partir do RGF (Anexos 1 e 6) e do RREO (Anexo 14) publicados no Siconfi.
Uso: python3 extrair_limites.py <pasta rgf com subpastas por ano> limites.json"""
import sys, os, re, glob, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lim_load import load
raiz, saida = sys.argv[1], sys.argv[2]
def nums(v): return [x for x in v if isinstance(x, float)]
def achar(rows, pre, i=0):
    for l, v in rows:
        if l.startswith(pre) and nums(v):
            n = nums(v); return n[i] if len(n) > i else None
    return None
PES = [('bruta','DESPESA BRUTA COM PESSOAL'),('ativo','Pessoal Ativo'),('venc','Vencimentos, Vantagens'),('patr','Obrigações Patronais'),('inat','Pessoal Inativo e Pensionistas'),
       ('apos','Aposentadorias'),('pens','Pensões'),('terc','Outras Despesas de Pessoal decorrentes de Contratos de Terceirização'),('naoexec','Despesa com Pessoal não Executada'),
       ('naocomp','DESPESAS NÃO COMPUTADAS'),('indeniz','Indenizações por Demissão'),('judic','Decorrentes de Decisão Judicial'),('dea','Despesas de Exercícios Anteriores'),
       ('inatvinc','Inativos e Pensionistas com Recursos Vinculados'),('acs','Agentes Comunitários'),('enferm','Parcela dedutível referente ao piso'),('outded','Outras Deduções Constitucionais'),
       ('liquida','DESPESA LÍQUIDA COM PESSOAL')]
def pos(rows, pre):
    """valor total 12 meses (a) e RPNP (b): colunas 12 e 13 da linha."""
    for l, v in rows:
        if l.startswith(pre):
            g = lambda i: v[i] if i < len(v) and isinstance(v[i], float) else 0.0
            return [g(12), g(13), [g(i) for i in range(12)]]
    return None
out = {'anos': {}}
for pasta in sorted(glob.glob(os.path.join(raiz, '20??'))):
    ano = os.path.basename(pasta); A = {'quads': [], 'q': {}, 'bims': [], 'b': {}}
    for f in sorted(glob.glob(os.path.join(pasta, '*RGF*QUADRIMESTRAL_*.xls'))):
        q = int(re.search(r'QUADRIMESTRAL_(\d)', f).group(1)); G = load(f); m = G['_meta']
        assert m['Exercício'] == ano and m['Período'].startswith('%dº' % q), (f, m)
        s6 = G['RGF-Anexo 06']; a1 = G['RGF-Anexo 01']
        rcl = s6['Receita Corrente Líquida']; dp = s6['Despesa com Pessoal']; dc = s6['Dívida Consolidada']; ga = s6['Garantias de Valores']; oc = s6['Operações de Crédito']; rp = s6.get('Restos a Pagar', [])
        rows = a1['Despesa com Pessoal']; ap = a1['Apuração do Cumprimento do Limite Legal']
        d = {'rcl': achar(rcl, 'Receita Corrente Líquida'), 'rcl_end': achar(rcl, 'Receita Corrente Líquida Ajustada para Cálculo dos Limites de Endividamento'), 'rcl_pes': achar(rcl, 'Receita Corrente Líquida Ajustada para Cálculo dos Limites da Despesa'),
             'dtp': achar(dp, 'Despesa Total com Pessoal'), 'dtp_p': achar(dp, 'Despesa Total com Pessoal', 1), 'dtp_lim': achar(dp, 'Limite Máximo'), 'dtp_lim_p': achar(dp, 'Limite Máximo', 1),
             'dtp_prud': achar(dp, 'Limite Prudencial'), 'dtp_prud_p': achar(dp, 'Limite Prudencial', 1), 'dtp_al': achar(dp, 'Limite de Alerta'), 'dtp_al_p': achar(dp, 'Limite de Alerta', 1),
             'dcl': achar(dc, 'Dívida Consolidada Líquida'), 'dcl_p': achar(dc, 'Dívida Consolidada Líquida', 1), 'dcl_lim': achar(dc, 'Limite Definido'), 'dcl_lim_p': achar(dc, 'Limite Definido', 1),
             'gar': achar(ga, 'Total das Garantias'), 'gar_p': achar(ga, 'Total das Garantias', 1), 'gar_lim': achar(ga, 'Limite Definido'), 'gar_lim_p': achar(ga, 'Limite Definido', 1),
             'oc': achar(oc, 'Operações de Crédito Internas'), 'oc_p': achar(oc, 'Operações de Crédito Internas', 1), 'oc_lim': achar(oc, 'Limite Definido pelo Senado Federal para Operações de Crédito Externas'), 'oc_lim_p': achar(oc, 'Limite Definido pelo Senado Federal para Operações de Crédito Externas', 1),
             'aro': achar(oc, 'Operações de Crédito por Antecipação'), 'aro_p': achar(oc, 'Operações de Crédito por Antecipação', 1), 'aro_lim': achar(oc, 'Limite Definido pelo Senado Federal para Operações de Crédito por Antecipação'), 'aro_lim_p': achar(oc, 'Limite Definido pelo Senado Federal para Operações de Crédito por Antecipação', 1),
             'rpnp': achar(rp, 'Valor Total'), 'caixa_rp': achar(rp, 'Valor Total', 1),
             'ded_emi': achar(ap, '(-) Transferências Obrigatórias da União Relativas às Emendas Individuais'), 'ded_ban': achar(ap, '(-) Transferências obrigatórias da União relativas às emendas de bancada'), 'ded_acs': achar(ap, '(-) Transferências da União relativas à remuneração')}
        d['pes'] = {k: pos(rows, p) for k, p in PES}
        mr = [r for l, r in rows if l == '' and r and r[0] == '<MR-11>']
        # conferências
        assert abs((d['pes']['liquida'][0] + d['pes']['liquida'][1]) - d['dtp']) < 1, (f, 'DTP')
        assert abs(d['pes']['bruta'][0] - d['pes']['naocomp'][0] - d['pes']['liquida'][0]) < 1, (f, 'I-II')
        assert abs(d['dtp'] / d['rcl_pes'] * 100 - d['dtp_p']) < 0.01, (f, '%')
        A['q'][q] = d; A['quads'].append(q)
    for f in sorted(glob.glob(os.path.join(pasta, '*RREO*BIMESTRAL_*.xls'))):
        b = int(re.search(r'BIMESTRAL_(\d)', f).group(1)); G = load(f); m = G['_meta']
        assert m['Exercício'] == ano and m['Período'].startswith('%dº' % b), (f, m)
        s = G['RREO-Anexo 14']; mde = s['Despesas com Manutenção e Desenvolvimento do Ensino']; sau = s['Despesas com Ações e Serviços Públicos de Saúde']; ocr = s['Receitas de Operações de Crédito e Despesas de Capital']
        rp = s.get('Resultados Primário e Nominal', [])
        A['b'][b] = {'mde': achar(mde, 'Mínimo Anual de <18% / 25%>'), 'mde_min': achar(mde, 'Mínimo Anual de <18% / 25%>', 1), 'mde_p': achar(mde, 'Mínimo Anual de <18% / 25%>', 2),
                     'fundeb': achar(mde, 'Mínimo Anual de 70% do FUNDEB'), 'fundeb_min': achar(mde, 'Mínimo Anual de 70% do FUNDEB', 1), 'fundeb_p': achar(mde, 'Mínimo Anual de 70% do FUNDEB', 2),
                     'asps': achar(sau, 'Despesas com Ações e Serviços Públicos de Saúde Executadas'), 'asps_min': achar(sau, 'Despesas com Ações e Serviços Públicos de Saúde Executadas', 1), 'asps_p': achar(sau, 'Despesas com Ações e Serviços Públicos de Saúde Executadas', 2),
                     'oc_rec': achar(ocr, 'Receitas de Operações de Crédito'), 'oc_rec_sal': achar(ocr, 'Receitas de Operações de Crédito', 1), 'dcap': achar(ocr, 'Despesa de Capital Líquida'), 'dcap_sal': achar(ocr, 'Despesa de Capital Líquida', 1)}
        A['bims'].append(b)
    out['anos'][ano] = A
    for q in A['quads']: print(ano, 'Q%d' % q, 'DTP %.2f%%' % A['q'][q]['dtp_p'], 'DCL %.2f%%' % A['q'][q]['dcl_p'], 'OC %.2f%%' % A['q'][q]['oc_p'], 'RP', A['q'][q]['rpnp'], A['q'][q]['caixa_rp'])
    for b in A['bims']: x = A['b'][b]; print(ano, 'B%d' % b, 'MDE', x['mde_p'], 'FUNDEB', x['fundeb_p'], 'ASPS', x['asps_p'], 'OC', x['oc_rec'], 'DCAP', x['dcap'])
json.dump(out, open(saida, 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
print('gravado', saida, os.path.getsize(saida))
