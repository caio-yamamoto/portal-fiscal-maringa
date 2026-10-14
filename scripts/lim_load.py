import re, xlrd
def load(path):
    wb = xlrd.open_workbook(path); res = {}; meta = {}
    for s in wb.sheets():
        q = '_'; quads = {'_':[]}
        for r in range(s.nrows):
            row = s.row_values(r); lab = re.sub(r'\s+', ' ', str(row[0])).strip()
            for k in ('Exercício:', 'Período:', 'Ente:', 'VERSÃO:'):
                if lab.startswith(k): meta[k[:-1]] = lab[len(k):].strip()
            if lab.startswith('Quadro:'):
                q = lab[7:].strip()
                if q in quads: q = q + ' #2'
                quads[q] = []; continue
            if not lab and not any(str(x).strip() for x in row): continue
            quads[q].append((lab, [v if isinstance(v, float) else (str(v).strip() or None) for v in row[1:]]))
        res[s.name] = quads
    res['_meta'] = meta; return res
