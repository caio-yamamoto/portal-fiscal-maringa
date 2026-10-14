import openpyxl, re, warnings
COD = re.compile(r'^\d(\.\d+){5,}\.?$')
FONTE = re.compile(r'^\d{3,6}$')
PER = re.compile(r'Período:\s*(\d{2})/(\d{2})/(\d{4})\s*a\s*(\d{2})/(\d{2})/(\d{4})')
EMI = re.compile(r'(\d{2})/(\d{2})/(\d{4}) - (\d{2}):(\d{2}):(\d{2})')
def ler(f):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore'); ws = openpyxl.load_workbook(f, data_only=True).worksheets[0]
    per = emi = total = None; fonte = None; fontes = {}; linhas = []; titulo = None
    for r in ws.iter_rows(values_only=True):
        for v in r:
            if isinstance(v, str):
                if PER.search(v): per = [int(x) for x in PER.search(v).groups()]
                if EMI.search(v): emi = EMI.search(v).group(0)
                if 'Receita Realizada por Fonte' in v: titulo = v.strip()
        c0 = str(r[0]).strip() if r[0] is not None else ''
        nums = [v for i, v in enumerate(r) if i > 0 and isinstance(v, (int, float)) and not isinstance(v, bool)]
        desc = next((v.strip() for v in r[1:] if isinstance(v, str) and v.strip()), '')
        if c0 == 'TOTAL:': total = float(nums[0]) if nums else None
        elif FONTE.match(c0): fonte = c0; fontes[c0] = [desc, float(nums[0]) if nums else 0.0]
        elif COD.match(c0) and fonte: linhas.append((fonte, c0, desc, float(nums[0]) if nums else 0.0))
    return {'titulo': titulo, 'per': per, 'emissao': emi, 'total': total, 'fontes': fontes, 'linhas': linhas}
