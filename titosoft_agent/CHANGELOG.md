# Changelog

## 0.2.0

- Adiciona ações remotas assinadas pela central via heartbeat outbound.
- Executa `backup_now` e `restart_addon` com allowlist e relatório de resultado.
- Persiste a chave pública da central recebida no enrollment/heartbeat.

## 0.1.2

- Inventário não envia mais entradas de "serviço" do HA (Supervisor, Core, OS,
  add-ons como Backup/SSH) nem entidades órfãs de sistema (sun, zone, automações).
  Só dispositivos físicos entram no CMDB. (Requer a central atualizada para
  remover os que já estavam listados.)

## 0.1.1

- Corrige inicialização como add-on: carrega o ambiente do container (s6-overlay)
  para enxergar o `SUPERVISOR_TOKEN`. Antes o add-on falhava com
  "SUPERVISOR_TOKEN ausente".

## 0.1.0

- Primeira versão: enrollment, heartbeat, inventário (Supervisor + REST/WebSocket)
  e backup full criptografado (AES-256-GCM) para storage S3-compatible.
