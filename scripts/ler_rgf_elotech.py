"""Lê os anexos do RGF emitidos mensalmente no Elotech (xlsx) e devolve um dicionário no mesmo formato
usado por extrair_limites.py / extrair_divida.py. Uso: python3 ler_rgf_elotech.py <pasta com os xlsx de um mês>"""
import sys, os, re, glob, json, warnings, unicodedata, openpyxl
warnings.filterwarnings('ignore')
MESES = ['JANEIRO','FEVEREIRO','MARÇO','ABRIL','MAIO','JUNHO','JULHO','AGOSTO','SETEMBRO','OUTUBRO','NOVEMBRO','DEZEMBRO']
def norm(s): s = unicodedata.normalize('NFD', str(s)); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn'); return re.sub(r'[^A-Z0-9%]', '', s.upper())
def num(c):
    if isinstance(c, (int, float)): return float(c)
    if isinstance(c, str) and re.fullmatch(r'-?\d+(\.\d+)?', c.strip()): return float(c)
    return None
def linhas(f):
    ws = openpyxl.load_workbook(f, data_only=True).worksheets[0]; out = []; meta = {}
    for r in ws.iter_rows(values_only=True):
        cel = [c for c in r if c not in (None, '')]
        if not cel: continue
        lab = str(cel[0]); vals = [num(c) for c in cel[1:]]; vals = [v for v in vals if v is not None]
        m = re.match(r'JANEIRO A (\w+) (\d{4})/MENSAL', lab)
        if m: meta['mes'] = MESES.index(m.group(1)) + 1; meta['ano'] = m.group(2)
        if 'ENTIDADES CONSOLIDADAS' in lab: meta['entidades'] = lab.split('ENTIDADES CONSOLIDADAS:')[1].strip()
        out.append((norm(lab), lab.strip(), vals))
    return out, meta
def achar(L, pre, i=0, n=1):
    p = norm(pre); k = 0
    for nl, lab, v in L:
        if nl.startswith(p) and v:
            k += 1
            if k == n: return v[i] if len(v) > i else None
    return None
def ler(pasta):
    arq = {k: (glob.glob(os.path.join(pasta, '*Anexo%s_*' % k)) + glob.glob(os.path.join(pasta, '*Anexo_%s_*' % k)) or [None])[0] for k in ('I','II','III','IV','VI')}
    R = {}; meta = {}
    L1, m1 = linhas(arq['I']); meta.update(m1)
    # anexo 1: 12 meses + total (a) + RPNP (b)
    PES = [('bruta','DESPESA BRUTA COM PESSOAL'),('ativo','Pessoal Ativo'),('venc','Vencimentos, Vantagens'),('patr','Obrigações Patronais'),('inat','Pessoal Inativo e Pensionistas'),
           ('apos','Aposentadorias'),('pens','Pensões'),('terc','Outras despesas de pessoal decorrentes de contratos de terceirização'),('naoexec','Despesa com Pessoal não Executada'),
           ('naocomp','DESPESAS NÃO COMPUTADAS'),('indeniz','Indenizações por Demissão'),('judic','Decorrentes de Decisão Judicial'),('dea','Despesas de Exercícios Anteriores'),
           ('inatvinc','Inativos e Pensionistas com Recursos Vinculados'),('acs','Agentes Comunitários'),('enferm','Parcela dedutível referente ao piso'),('outded','Outras Deduções Constitucionais'),
           ('liquida','DESPESA LÍQUIDA COM PESSOAL')]
    pes = {}
    for k, p in PES:
        tot = [v for nl, lab, v in L1 if nl.startswith(norm(p)) and len(v) >= 14]
        if k == 'terc': tot = [[sum(x) for x in zip(*tot)]] if tot else []   # Elotech separa elemento 34 e demais; o Siconfi soma
        pes[k] = [tot[0][12], tot[0][13], tot[0][:12]] if tot else None
    d = {'pes': pes, 'rcl': achar(L1, 'RECEITA CORRENTE LÍQUIDA - RCL'), 'rcl_pes': achar(L1, 'RECEITA CORRENTE LÍQUIDA AJUSTADA PARA CÁLCULO DOS LIMITES DA DESPESA'),
         'dtp': achar(L1, 'DESPESA TOTAL COM PESSOAL'), 'dtp_p': achar(L1, 'DESPESA TOTAL COM PESSOAL', 1),
         'dtp_lim': achar(L1, 'LIMITE MÁXIMO'), 'dtp_lim_p': 54.0, 'dtp_prud': achar(L1, 'LIMITE PRUDENCIAL'), 'dtp_prud_p': 51.3, 'dtp_al': achar(L1, 'LIMITE DE ALERTA'), 'dtp_al_p': 48.6,
         'ded_emi': achar(L1, '(-) Transferências obrigatórias da União relativas às emendas individu'), 'ded_ban': achar(L1, '(-) Transferências obrigatórias da União relativas às emendas de banca'), 'ded_acs': achar(L1, '(-) Recursos destinados ao pagamento dos agentes')}
    # anexo 2: colunas 0 = exercício anterior, 1..3 = quadrimestres; o mês corrente cai na coluna do quadrimestre em curso
    L2, m2 = linhas(arq['II']); qc = (meta['mes'] - 1) // 4 + 1
    DK = [('dc','DÍVIDA CONSOLIDADA - DC'),('contr','Dívida Contratual'),('emp','Empréstimos'),('emp_int','Internos'),('emp_ext','Externos'),('reest','Reestruturação da Dívida'),('fin','Financiamentos'),
          ('parc','Parcelamento e Renegociação'),('parc_trib','De Tributos'),('parc_prev','De Contribuições Previdenciárias'),('prec','Precatórios Posteriores a 05/05/2000 (inclusive)'),('outras','Outras Dívidas'),
          ('ded','DEDUÇÕES'),('caixa','Disponibilidade de Caixa Bruta'),('rpp','(-) Restos a Pagar Processados'),('dep','(-) Depósitos Restituíves'),('haveres','Demais Haveres Financeiros'),
          ('dcl','DÍVIDA CONSOLIDADA LÍQUIDA'),('rcl_aj','RECEITA CORRENTE LÍQUIDA AJUSTADA'),('pdc','% da DC sobre'),('pdcl','% da DCL sobre'),
          ('prec_ant','PRECATÓRIOS ANTERIORES'),('prec_fora','PRECATÓRIOS POSTERIORES A 05/05/2000 (Não incluídos'),('atuarial','PASSIVO ATUARIAL'),('rpnp','RP NÃO-PROCESSADOS'),('aro','ANTECIPAÇÕES DE RECEITA'),('ppp','DÍVIDA CONTRATUAL DE PPP'),('depjud','APROPRIAÇÃO DE DEPÓSITOS')]
    div = {k: achar(L2, p, qc) for k, p in DK}; div_ant = {k: achar(L2, p, 0) for k, p in DK}
    d.update({'dcl': div['dcl'], 'dcl_p': div['pdcl'], 'rcl_end': div['rcl_aj'], 'dcl_lim': achar(L2, 'LIMITE DEFINIDO POR RESOLUÇÃO', qc), 'dcl_lim_p': 120.0})
    L3, _ = linhas(arq['III'])
    d.update({'gar': achar(L3, 'TOTAL GARANTIAS CONCEDIDAS', qc), 'gar_p': achar(L3, '% do TOTAL DAS GARANTIAS', qc), 'gar_lim': achar(L3, 'LIMITE DEFINIDO POR RESOLUÇÃO', qc), 'gar_lim_p': 22.0})
    L4, _ = linhas(arq['IV'])
    d.update({'oc': achar(L4, 'TOTAL CONSIDERADO PARA FINS'), 'oc_p': achar(L4, 'TOTAL CONSIDERADO PARA FINS', 1), 'oc_lim': achar(L4, 'LIMITE GERAL DEFINIDO'), 'oc_lim_p': 16.0,
              'aro': achar(L4, 'OPERAÇÕES DE CRÉDITO POR ANTECIPAÇÃO'), 'aro_p': achar(L4, 'OPERAÇÕES DE CRÉDITO POR ANTECIPAÇÃO', 1), 'aro_lim': achar(L4, 'LIMITE DEFINIDO POR RESOLUÇÃO DO SENADO FEDERAL PARA AS OPERAÇÕES DE C'), 'aro_lim_p': 7.0,
              'oc_mes': achar(L4, 'TOTAL (III)'), 'oc_ate': achar(L4, 'TOTAL (III)', 1)})
    L6, _ = linhas(arq['VI'])
    d.update({'rpnp': achar(L6, 'Valor Total'), 'caixa_rp': achar(L6, 'Valor Total', 1), 'dcl_vi': achar(L6, 'Dívida Consolidada Líquida'), 'dcl_vi_p': achar(L6, 'Dívida Consolidada Líquida', 1)})
    # conferências internas
    assert abs(pes['liquida'][0] + pes['liquida'][1] - d['dtp']) < 1, 'DTP'
    assert abs(pes['bruta'][0] - pes['naocomp'][0] - pes['liquida'][0]) < 1, 'I-II'
    return {'meta': meta, 'lim': d, 'div': div, 'div_ant': div_ant}
if __name__ == '__main__':
    r = ler(sys.argv[1]); print(json.dumps(r['meta'], ensure_ascii=False))
    for k in ('rcl','rcl_pes','dtp','dtp_p','dcl','dcl_p','gar_lim','oc','oc_p','rpnp','caixa_rp','dcl_vi'): print(k, r['lim'][k])
