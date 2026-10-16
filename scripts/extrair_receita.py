import sys, os, glob, re, json, collections, warnings, openpyxl, pickle, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ler_fonte
raw, quadros, saida = sys.argv[1], sys.argv[2], sys.argv[3]
MES = {'JANEIRO': 1, 'FEVEREIRO': 2, 'MARÇO': 3, 'ABRIL': 4, 'MAIO': 5, 'JUNHO': 6, 'JULHO': 7, 'AGOSTO': 8, 'SETEMBRO': 9, 'OUTUBRO': 10, 'NOVEMBRO': 11, 'DEZEMBRO': 12}
# cache das planilhas já lidas (como em extrair_despesa.py): só relê o que mudou, em geral os dois meses reemitidos
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'cache_rec'); os.makedirs(CACHE, exist_ok=True)
def com_cache(f, ler):
    st = os.stat(f)
    c = os.path.join(CACHE, hashlib.md5(('%s|%s|%d|%d' % (ler.__name__, os.path.abspath(f), st.st_size, int(st.st_mtime))).encode()).hexdigest() + '.pkl')
    if os.path.exists(c):
        with open(c, 'rb') as h: return pickle.load(h)
    d = ler(f)
    with open(c, 'wb') as h: pickle.dump(d, h)
    return d
def ler_quadro(f):
    """[(código, descrição)] das linhas do Quadro das Receitas por Natureza."""
    with warnings.catch_warnings():
        warnings.simplefilter('ignore'); ws = openpyxl.load_workbook(f, data_only=True).worksheets[0]
    out = []
    for r in ws.iter_rows(values_only=True):
        c0 = str(r[0]).strip() if r[0] is not None else ''
        if ler_fonte.COD.match(c0):
            d = next((v.strip() for v in r[1:] if isinstance(v, str) and v.strip()), '')
            if d: out.append((c0, d))
    return out
def ler_planilha(f):
    """('prev', [(fonte, natureza, [12 meses], orçado)]) para a Previsão Orçamentária; ('real', ler_fonte.ler) para a receita realizada."""
    with warnings.catch_warnings():
        warnings.simplefilter('ignore'); wb = openpyxl.load_workbook(f, data_only=True, read_only=True)
    ws0 = wb.worksheets[0]; cab = next(ws0.iter_rows(min_row=1, max_row=1, values_only=True))
    if cab and cab[0] == 'ENT.' and 'ORÇADO' in [str(x) for x in cab]:
        i_orc = list(cab).index('ORÇADO'); meses_col = [list(cab).index(m) for m in MES]
        linhas = [(str(r[0]), str(r[2]).strip(), [float(r[c] or 0) for c in meses_col], float(r[i_orc] or 0))
                  for r in ws0.iter_rows(min_row=2, values_only=True) if r[2]]
        wb.close(); return ('prev', linhas)
    wb.close()
    return ('real', ler_fonte.ler(f))
avisos = []
# nomes das naturezas: Quadro das Receitas por Natureza (todas as linhas, primeira descrição de cada código)
nomes = {}
for f in sorted(glob.glob(os.path.join(quadros, '*.xlsx'))):
    for c0, d in com_cache(f, ler_quadro):
        if c0 not in nomes: nomes[c0] = d
print('nomes de natureza:', len(nomes))
anos = {}
for pasta in sorted(glob.glob(os.path.join(raw, '20??'))):
    ano = int(os.path.basename(pasta)); real = {}; prev = {}; fontes = {}; emissoes = {}
    for f in sorted(glob.glob(os.path.join(pasta, '*.xlsx'))):
        tipo, conteudo = com_cache(f, ler_planilha)
        if tipo == 'prev':
            for fc, nat, v, orc in conteudo:
                k = (fc, nat)
                if abs(sum(v) - orc) > 1: avisos.append('previsão %s: soma dos meses difere do orçado (%.2f x %.2f)' % (k, sum(v), orc))
                p = prev.setdefault(k, [0.0] * 12)
                for i in range(12): p[i] += v[i]
            print(ano, 'previsão lida de', os.path.basename(f), len(prev), 'pares fonte+natureza'); continue
        R = conteudo
        if not R['titulo'] or not R['per']: avisos.append('ignorado: ' + os.path.basename(f)); continue
        d1, m1, a1, d2, m2, a2 = R['per']
        if a1 != ano or (m1, a1) != (m2, a2) or d1 != 1: avisos.append('período inesperado em %s: %s' % (os.path.basename(f), R['per'])); continue
        if m1 in emissoes: avisos.append('mês %d repetido; usei %s' % (m1, os.path.basename(f)))
        emissoes[m1] = R['emissao']
        for fc, (d, v) in R['fontes'].items(): fontes[fc] = d
        tot = 0.0
        for fc, c, d, v in R['linhas']:
            real.setdefault((fc, c), [0.0] * 12)[m1 - 1] += v; tot += v
            if c not in nomes: nomes[c] = d
        for fc, (d, v) in R['fontes'].items():
            s = sum(x[3] for x in R['linhas'] if x[0] == fc)
            if abs(s - v) > 0.01: avisos.append('%d/%d: fonte %s soma %.2f x total da fonte %.2f' % (m1, ano, fc, s, v))
    meses = sorted(emissoes)
    if meses != list(range(1, len(meses) + 1)): avisos.append('%d: meses faltando: %s' % (ano, meses))
    itens = []
    for k in sorted(set(prev) | set(real)):
        itens.append([k[0], k[1], [round(x, 2) for x in prev.get(k, [0.0] * 12)], [round(x, 2) for x in real.get(k, [0.0] * 12)]])
    so_real = [k for k in real if k not in prev]
    if so_real: avisos.append('%d: %d pares fonte+natureza com arrecadação sem previsão (ex.: %s)' % (ano, len(so_real), so_real[:3]))
    import calendar, datetime
    parcial = None
    for m in meses:
        e = emissoes.get(m)
        if e:
            dd, mm, aa = int(e[0:2]), int(e[3:5]), int(e[6:10])
            if datetime.date(aa, mm, dd) <= datetime.date(ano, m, calendar.monthrange(ano, m)[1]): parcial = m
    anos[str(ano)] = {'meses': len(meses), 'emissoes': {str(m): emissoes[m] for m in meses}, 'parcial': parcial, 'itens': itens, 'fontes': fontes}
    print(ano, 'meses', meses, '| itens', len(itens), '| previsto', round(sum(sum(i[2]) for i in itens), 2), '| realizado', round(sum(sum(i[3]) for i in itens), 2))
usados = {i[1] for a in anos.values() for i in a['itens']}
# nomes dos níveis superiores (código com zeros à direita)
def pad(segs):
    base = ['0', '0', '0', '0', '00', '0', '0', '00', '00', '00', '00', '00']
    for i, s in enumerate(segs): base[i] = s
    return '.'.join(base) + '.'
precisa = set()
for c in usados:
    s = c.rstrip('.').split('.')
    for n in range(1, 13): precisa.add(pad(s[:n]))
nomes_out = {c: nomes[c] for c in sorted(precisa) if c in nomes}   # ordenado: o arquivo sai igual se nada mudou
faltam = sorted(c for c in usados if c not in nomes)
if faltam: avisos.append('naturezas sem nome: %s' % faltam[:5])
json.dump({'anos': anos, 'nomes': nomes_out}, open(saida, 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
print('nomes usados', len(nomes_out), '| tamanho', os.path.getsize(saida))
for a in avisos: print('AVISO', a)
