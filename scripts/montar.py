import sys, os, gzip, base64
tpl, css, data, out = sys.argv[1:5]
desp = sys.argv[5] if len(sys.argv) > 5 else None
d = os.path.dirname(os.path.abspath(data))
gz = lambda b: base64.b64encode(gzip.compress(b, 9, mtime=0)).decode()
ler = lambda nome: open(os.path.join(d, nome), encoding='utf8').read() if os.path.exists(os.path.join(d, nome)) else '{"anos":{}}'
t = open(tpl, encoding='utf8').read().replace('__CSS__', open(css, encoding='utf8').read())
# receita e despesa vão compactadas (gzip + base64); o navegador descompacta ao abrir
t = t.replace('__DATAGZ__', gz(open(data, 'rb').read()))
t = t.replace('__DESPGZ__', gz(open(desp, 'rb').read() if desp else b'{"anos":{}}'))
t = t.replace('__DIV__', ler('divida.json')).replace('__LIM__', ler('limites.json')).replace('__MET__', ler('metas.json'))
assert '__DATA' not in t and '__DESP' not in t
open(out, 'w', encoding='utf8').write(t)
print(out, os.path.getsize(out), 'bytes')
