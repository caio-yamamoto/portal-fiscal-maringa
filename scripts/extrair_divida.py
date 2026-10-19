"""Gera divida.json a partir do RGF (Siconfi): Anexo 2 (Dívida Consolidada Líquida) e Anexo 4 (Operações de Crédito).
Uso: python3 extrair_divida.py <pasta com subpastas por ano contendo SICONFI_RGF_*_QUADRIMESTRAL_n.xls> divida.json"""
import sys, os, re, glob, json, xlrd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from campos_siconfi import DK
raiz, saida = sys.argv[1], sys.argv[2]
def load(path):
    wb = xlrd.open_workbook(path); res = {}; meta = {}
    for s in wb.sheets():
        q = None; quads = {}
        for r in range(s.nrows):
            row = s.row_values(r); lab = re.sub(r'\s+', ' ', str(row[0])).strip()
            for k in ('Exercício:', 'Período:', 'Ente:', 'VERSÃO:'):
                if lab.startswith(k): meta[k[:-1]] = lab[len(k):].strip()
            if lab.startswith('Quadro:'):
                q = lab[7:].strip()
                if q in quads: q = q + ' #2'
                quads[q] = []; continue
            if q is None or not lab: continue
            quads[q].append((lab, [v if isinstance(v, float) else (str(v).strip() or None) for v in row[1:]]))
        res[s.name] = quads
    res['_meta'] = meta; return res
def nums(v): return [x for x in v if isinstance(x, float)]
def col(rows, pre, i):
    for l, v in rows:
        if l.startswith(pre):
            # as linhas "Internos"/"Externos" aparecem duas vezes (empréstimos e financiamentos): fica a primeira
            return (v[i] if i < len(v) and isinstance(v[i], float) else None)
    return None
out = {'anos': {}}; avisos = []
for pasta in sorted(glob.glob(os.path.join(raiz, '20??'))):
    ano = os.path.basename(pasta); A = {'quads': [], 'anterior': None, 'q': {}, 'opc': {}, 'notas': {}}
    for f in sorted(glob.glob(os.path.join(pasta, '*RGF*QUADRIMESTRAL_*.xls'))):
        q = int(re.search(r'QUADRIMESTRAL_(\d)', f).group(1)); G = load(f); m = G['_meta']
        assert m['Exercício'] == ano and m['Período'].startswith('%dº' % q), (f, m)
        rows = G['RGF-Anexo 02']['Demonstrativo da Dívida Consolidada Líquida']
        # colunas de valores: 0 = saldo do exercício anterior; 1..3 = até o 1º..3º quadrimestre
        A['q'][q] = {k: col(rows, p, q) for k, p in DK}
        ant = {k: col(rows, p, 0) for k, p in DK}
        if A['anterior'] is None: A['anterior'] = ant
        elif abs((ant['dc'] or 0) - (A['anterior']['dc'] or 0)) > 0.01: avisos.append('%s: saldo anterior difere entre quadrimestres' % ano)
        notas = [x for l, v in G['RGF-Anexo 02'].get('Notas Explicativas', []) for x in v if isinstance(x, str) and len(x) > 30]
        if notas: A['notas'][q] = notas[0]
        r4 = G['RGF-Anexo 04']; oc = r4['Operações de Crédito']; ap = r4['Apuração do Cumprimento dos Limites']
        tot = [v for l, v in oc if l.startswith('TOTAL (III)')][0]
        def ap_(pre, i=0):
            for l, v in ap:
                if l.startswith(pre): n = nums(v); return n[i] if len(n) > i else None
        A['opc'][q] = {'no_quad': nums(tot)[0] if nums(tot) else 0, 'ate_quad': nums(tot)[1] if len(nums(tot)) > 1 else 0,
                       'considerado': ap_('TOTAL CONSIDERADO'), 'pct': ap_('TOTAL CONSIDERADO', 1), 'limite': ap_('LIMITE GERAL'), 'alerta': ap_('LIMITE DE ALERTA'), 'rcl_aj': ap_('RECEITA CORRENTE LÍQUIDA AJUSTADA')}
        A['quads'].append(q)
        d = A['q'][q]
        # conferências
        def chk(a, b, nome):
            if a is None or b is None or abs(a - b) > 1: avisos.append('%s Q%d: %s (%s x %s)' % (ano, q, nome, a, b))
        chk((d['dc'] or 0) - (d['ded'] or 0), d['dcl'], 'DC - deduções = DCL')
        chk((d['mob'] or 0) + (d['contr'] or 0) + (d['prec'] or 0) + (d['outras'] or 0), d['dc'], 'componentes = DC')
        chk((d['emp'] or 0) + (d['reest'] or 0) + (d['fin'] or 0) + (d['parc'] or 0) + (d['demais'] or 0), d['contr'], 'componentes = contratual')
        chk((d['caixa'] or 0) - (d['rpp'] or 0) - (d['dep'] or 0) + (d['haveres'] or 0), d['ded'], 'caixa - RP - depósitos = deduções')
    A['quads'].sort(); out['anos'][ano] = A
    print(ano, 'quadrimestres', A['quads'], '| DC anterior %.1f mi' % (A['anterior']['dc'] / 1e6), '| DC', ['%.1f' % (A['q'][q]['dc'] / 1e6) for q in A['quads']], '| DCL', ['%.1f' % (A['q'][q]['dcl'] / 1e6) for q in A['quads']], '| %DCL', [A['q'][q]['pdcl'] for q in A['quads']])
anos = sorted(out['anos'])
for a, b in zip(anos, anos[1:]):
    A, B = out['anos'][a], out['anos'][b]
    if 3 in A['q'] and abs(A['q'][3]['dc'] - B['anterior']['dc']) > 1: avisos.append('DC do 3º quad de %s (%.2f) difere do saldo anterior de %s (%.2f)' % (a, A['q'][3]['dc'], b, B['anterior']['dc']))
for x in avisos: print('AVISO:', x)
json.dump(out, open(saida, 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
print('gravado', saida, os.path.getsize(saida))
