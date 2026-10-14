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
cp site/index.html index.html
