"""Gera despesa.json a partir dos balancetes da despesa (modelo analítico, de 01/01 até o fim de cada mês).
Uso: python3 extrair_despesa.py <pasta com subpastas desp2025, desp2026...> despesa.json"""
import sys, os, re, glob, json, datetime, calendar
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ler_despesa import ler as _ler
import pickle, hashlib
from multiprocessing import Pool
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'cache_desp'); os.makedirs(CACHE, exist_ok=True)
def _cpath(f):
    st = os.stat(f); return os.path.join(CACHE, hashlib.md5(('%s|%d|%d' % (os.path.abspath(f), st.st_size, int(st.st_mtime))).encode()).hexdigest() + '.pkl')
def ler_cache(f):
    c = _cpath(f)
    if os.path.exists(c):
        with open(c, 'rb') as h: return pickle.load(h)
    d = _ler(f)
    with open(c, 'wb') as h: pickle.dump(d, h)
    return d
_MEM = {}
def ler(f): return _MEM[f] if f in _MEM else ler_cache(f)

def main():
    raiz, saida = sys.argv[1], sys.argv[2]
    r2 = lambda v: round(v + 0.0, 2)
    out = {'anos': {}}
    if True:  # leitura paralela dos arquivos (com cache)
        todos = [f for p in sorted(glob.glob(os.path.join(raiz, 'desp20??'))) for f in sorted(glob.glob(os.path.join(p, '*analitico*.xlsx')))]
        with Pool(min(8, os.cpu_count() or 2)) as pool:
            for f, d in zip(todos, pool.map(ler_cache, todos)): _MEM[f] = d
    for pasta in sorted(glob.glob(os.path.join(raiz, 'desp20??'))):
        ano = pasta[-4:]; meses = {}
        for f in sorted(glob.glob(os.path.join(pasta, '*analitico*.xlsx'))):
            d = ler(f)
            if not d['analitico']:
                continue  # o simplificado (só do mês) não é necessário
            m1, a1, m2, a2 = d['per']
            if str(a2) != ano: print('AVISO: %s é de %s, não de %s' % (f, a2, ano)); continue
            if m1 != 1: print('AVISO: %s não começa em janeiro (período %s); emita de 01/01 até o fim do mês' % (f, d['per'])); continue
            if m2 in meses: print('AVISO: mês %d repetido; ficou o último arquivo' % m2)
            meses[m2] = (f, d)
        if not meses: continue
        n = max(meses)
        falta = [m for m in range(1, n+1) if m not in meses]
        if falta: print('AVISO %s: faltam os meses %s; os meses seguintes ficam sem a separação mensal correta' % (ano, falta))
        chaves = {}; itens = []; acoes = {}; elnomes = {}; subnomes = {}; subs = {}
        emis = {}; parcial = None
        for m in range(1, n+1):
            if m not in meses: continue
            f, d = meses[m]
            emis[m] = d['emissao']
            if d['emissao']:
                dd, mm, aa = map(int, d['emissao'][:10].split('/'))
                fim = datetime.date(int(ano), m, calendar.monthrange(int(ano), m)[1])
                if datetime.date(aa, mm, dd) <= fim: parcial = m
            for k, v in d['acoes'].items(): acoes['.'.join(k)] = v
            for j, x in enumerate(d['dot']):
                key = ('.'.join(x['prog']), x['nat'], x['fonte'])
                if key not in chaves:
                    chaves[key] = len(itens)
                    itens.append({'k': key, 'ini': 0, 'atu': [0]*n, 'res': [0]*n, 'emp': [0]*n, 'liq': [0]*n, 'pago': [0]*n})
                it = itens[chaves[key]]
                it['ini'] = x['inicial']; it['atu'][m-1] = x['atual']; it['res'][m-1] = x['res']
                for q in ('emp', 'liq', 'pago'): it[q][m-1] = x[q]   # acumulado até m (convertido abaixo)
                elnomes[x['nat']] = x['natnome']
            for u in d['sub']:
                x = d['dot'][u['dot']]; key = ('.'.join(x['prog']), x['nat'], x['fonte']); sk = (key, u['cod'])
                subnomes[u['cod']] = u['nome']
                if sk not in subs: subs[sk] = {'emp': [0]*n, 'liq': [0]*n, 'pago': [0]*n}
                for q in ('emp', 'liq', 'pago'): subs[sk][q][m-1] = u[q]
        # acumulado -> mensal (meses ausentes repetem o acumulado anterior)
        def mensal(a):
            res = []; ant = 0
            for m in range(n):
                if (m+1) in meses: res.append(r2(a[m] - ant)); ant = a[m]
                else: res.append(0)
            return res
        def prop(a):  # dotação atualizada: posição no fim de cada mês
            res = []; ant = 0
            for m in range(n):
                if (m+1) in meses: ant = a[m]
                res.append(r2(ant))
            return res
        L = []; idx = {}
        for it in itens:
            emp, liq, pago, atu, res = mensal(it['emp']), mensal(it['liq']), mensal(it['pago']), prop(it['atu']), prop(it['res'])
            if not it['ini'] and not any(atu) and not any(emp) and not any(liq) and not any(pago): continue
            idx[it['k']] = len(L)
            L.append(list(it['k']) + [r2(it['ini']), atu, emp, liq, pago, res])
        S = []
        for (key, cod), v in subs.items():
            if key not in idx: continue
            e, l, p = mensal(v['emp']), mensal(v['liq']), mensal(v['pago'])
            if any(e) or any(l) or any(p): S.append([idx[key], cod, e, l, p])
        out['anos'][ano] = {'meses': n, 'emissoes': emis, 'parcial': parcial, 'itens': L, 'subs': S, 'acoes': acoes, 'elnomes': elnomes, 'subnomes': subnomes}
        tot = lambda q: round(sum(sum(x[{'emp': 5, 'liq': 6, 'pago': 7}[q]]) for x in L), 2)
        print('%s: %d meses (parcial=%s), %d dotações, %d subelementos; inicial %.2f, atualizada %.2f; empenhado %.2f, liquidado %.2f, pago %.2f' % (
            ano, n, parcial, len(L), len(S), sum(x[3] for x in L), sum(x[4][n-1] for x in L), tot('emp'), tot('liq'), tot('pago')))
    json.dump(out, open(saida, 'w'), ensure_ascii=False, separators=(',', ':'))
    print('gravado', saida, os.path.getsize(saida), 'bytes')

if __name__ == '__main__':
    main()  # protegido: no Windows, o Pool reimporta este módulo em cada processo
