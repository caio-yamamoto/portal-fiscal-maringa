#!/usr/bin/env bash
# Atualiza os dados a partir dos relatórios (se existirem) e monta o portal em site/index.html.
set -euo pipefail
cd "$(dirname "$0")/.."
R=relatorios
if compgen -G "$R/20??/*.xlsx" > /dev/null; then
  echo "== receita"; python3 scripts/extrair_receita.py "$R" "$R/quadros" dados/receita.json
fi
if compgen -G "$R/desp20??/*analitico*.xlsx" > /dev/null; then
  echo "== despesa"; python3 scripts/extrair_despesa.py "$R" dados/despesa.json
fi
if compgen -G "$R/rgf/20??/*.xls" > /dev/null; then
  echo "== dívida, limites e metas"
  python3 scripts/extrair_divida.py "$R/rgf" dados/divida.json
  python3 scripts/extrair_limites.py "$R/rgf" dados/limites.json
  python3 scripts/extrair_metas.py "$R/rgf" dados/metas.json
fi
mkdir -p site
python3 scripts/montar.py src/portal.html src/base.css dados/receita.json site/index.html dados/despesa.json
# o GitHub Pages serve o arquivo como está: envolve o portal num documento HTML completo
python3 - <<'PY'
p = 'site/index.html'; t = open(p, encoding='utf8').read()
if not t.lstrip().lower().startswith('<!doctype'):
    t = '<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n' + t.replace('</style>', '</style>\n</head>\n<body>', 1) + '\n</body>\n</html>\n'
    open(p, 'w', encoding='utf8').write(t)
PY
cp site/index.html index.html
