"""Leitura do 'Balancete da despesa' (Elotech), modelo analítico, emitido de 01/01 até o fim do mês."""
import re, openpyxl
PROG = re.compile(r'^(\d{2})\.(\d{3})\.(\d{2})\.(\d{3})\.(\d{4})\.(\d{4}) - (.*)$', re.S)
DOT = re.compile(r'^\d+$')
NAT = re.compile(r'^(\d\.\d\.\d{2}\.\d{2})\.00\.00 - (.*)$', re.S)
SUB = re.compile(r'^\d\.\d\.\d{2}\.\d{2}\.\d{2}\.\d{2}$')
PER = re.compile(r'Período:\s*(\w+)/(\d{4})\s*até\s*(\w+)/(\d{4})')
EMI = re.compile(r'(\d{2})/(\d{2})/(\d{4}) - (\d{2}):(\d{2}):(\d{2})')
MESES = ['janeiro','fevereiro','março','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro']
num = lambda v: isinstance(v, (int, float))

def ler(f):
    ws = openpyxl.load_workbook(f, data_only=True).worksheets[0]
    rows = [[c for c in r if c is not None] for r in ws.iter_rows(values_only=True)]
    out = {'per': None, 'emissao': None, 'analitico': False, 'acoes': {}, 'dot': [], 'sub': [], 'total': None}
    prog = None; pend = None; ult = None; i = 0
    while i < len(rows):
        r = rows[i]; i += 1
        if not r: continue
        a = r[0]
        if isinstance(a, str):
            m = PER.search(a)
            if m and not out['per']:
                out['per'] = (MESES.index(m.group(1).lower())+1, int(m.group(2)), MESES.index(m.group(3).lower())+1, int(m.group(4)))
                continue
            if a == 'Fixada\nAutorizada': out['analitico'] = True; continue
            if a == 'Totais':
                nx = rows[i] if i < len(rows) else []
                out['total'] = nx if nx and num(nx[0]) else r[1:]
                continue
            if a.startswith('FONTE: Sistema Elotech') and len(r) > 1:
                m = EMI.search(str(r[1])); out['emissao'] = m.group(0) if m else None; continue
            m = PROG.match(a)
            if m:
                prog = m.groups()[:6]; out['acoes'][prog] = re.sub(r'\s+', ' ', m.group(7)).strip(); continue
            if DOT.match(a) and len(r) == 11 and r[1] in ('O', 'E', 'C', 'X') or (DOT.match(a) and len(r) == 11):
                nm = NAT.match(r[2])
                if not nm: raise ValueError('natureza inesperada: %r' % (r[2],))
                nx = rows[i]; i += 1
                if not (len(nx) == 7 and all(num(x) for x in nx)): raise ValueError('linha 2 da dotação inesperada perto de %r' % (r,))
                d = {'red': a, 'prog': prog, 'nat': nm.group(1), 'natnome': re.sub(r'\s+', ' ', nm.group(2)).strip(), 'fonte': str(r[3]),
                     'inicial': r[4], 'atual': nx[0], 'res': nx[2], 'emp': nx[3], 'liq': nx[4], 'pago': nx[5], 'saldo': nx[6]}
                out['dot'].append(d); ult = d; continue
            if SUB.match(a) and len(r) == 6 and ult is not None:
                out['sub'].append({'dot': len(out['dot'])-1, 'cod': a, 'nome': re.sub(r'\s+', ' ', str(r[1])).strip(), 'emp': r[2], 'liq': r[3], 'pago': r[4]})
                continue
    return out
