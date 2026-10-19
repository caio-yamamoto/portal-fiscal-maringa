# Robô de atualização do portal

Emite os relatórios no sistema contábil, gera os dados do portal, confere com o balancete simplificado e
envia ao GitHub. O site é republicado automaticamente.

## Preparação (uma vez)

1. Instale o **Python 3.10+**, o **Git** e o **Google Chrome**.
2. Clone o repositório: `git clone https://github.com/caio-yamamoto/portal-fiscal-maringa.git`
   (o Git pede o login do GitHub na primeira vez e guarda a credencial).
3. Instale as bibliotecas: `pip install selenium openpyxl`
4. Copie o seu `automacao_relatorios_bi.py` para a pasta `robo/` (ele não vai para o GitHub).
5. Coloque o histórico de relatórios em `relatorios_locais/`, na raiz do repositório:

   ```
   relatorios_locais/
     2025/  2026/      receita realizada por fonte (um por mês) e a Previsão Orçamentária do ano
     quadros/          Anexo 2 – quadro da receita por natureza (nomes das naturezas)
     desp2025/ desp2026/  balancetes da despesa analíticos (01/01 até o fim de cada mês) e simplificados
   ```

   Essa pasta não vai para o GitHub (está no `.gitignore`).

## Uso

```
cd portal-fiscal-maringa\robo
python robo_portal.py
```

- O Chrome abre na tela do sistema. Se pedir login, entre normalmente (usuário, senha e "Confirme que é humano").
- O robô emite, para o mês vigente e o anterior: receita realizada por fonte, balancete analítico
  (acumulado desde 01/01) e balancete simplificado.
- Busca no Siconfi (pela API de dados abertos, sem captcha) os RGF e RREO novos ou retificados, que alimentam as abas
  Dívida consolidada, Metas fiscais e Limites legais. Se a API estiver fora do ar, só aparece um aviso.
- Em seguida gera os dados, confere com o simplificado e envia ao GitHub. Se a conferência apontar diferença,
  nada é enviado e a mensagem explica o que fazer.

Outros comandos:

- `python robo_portal.py --sem-envio` – emite e gera, sem enviar.
- `python atualizar_portal.py` – só gera, confere e envia (sem abrir o sistema), útil quando os relatórios já foram baixados.
- `python atualizar_portal.py --forcar` – envia os dados já gerados sem conferir de novo. Use depois que a
  conferência apontou uma diferença de causa conhecida (ex.: lançamentos feitos durante a emissão, no mês aberto).

## Pergunta automática em dias úteis

`iniciar_com_windows.py` mostra a janela "Deseja atualizar o Portal Fiscal agora?" (Sim / Não), só de segunda
a sexta:

- ao entrar no Windows (na primeira vez do dia), depois que a internet estiver disponível;
- às 13:10.

Com **Sim**, abre uma janela de terminal com o robô; ao terminar, ela mostra o resumo (enviado, nada mudou,
diferença na conferência ou erro) e espera um Enter. Com **Não**, ou sem resposta em 30 minutos, nada acontece.
Cada execução fica registrada em `robo\logs\`.

As duas tarefas do Agendador ("Portal Fiscal - ao entrar no Windows" e "Portal Fiscal - 13h10") são criadas por:

```
cd portal-fiscal-maringa\robo
powershell -ExecutionPolicy Bypass -File agendar_no_windows.ps1
```

Para desativar, abra o Agendador de Tarefas, procure as tarefas "Portal Fiscal" e clique em Desabilitar
(ou rode `Unregister-ScheduledTask -TaskName "Portal Fiscal*" -Confirm:$false` para removê-las).
