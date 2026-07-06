#!/usr/bin/env sh
# Entrypoint do add-on: converte /data/options.json em variáveis de ambiente
# e inicia o agente. SUPERVISOR_TOKEN é injetado automaticamente pelo Supervisor.
set -e

OPTIONS=/data/options.json

if [ -f "$OPTIONS" ]; then
  get_opt() {
    python3 -c "import json,sys; v=json.load(open('$OPTIONS')).get('$1',''); print(v if v is not None else '')"
  }
  export TITOSOFT_API_URL="$(get_opt api_base_url)"
  export ENROLLMENT_TOKEN="$(get_opt enrollment_token)"
  export HEARTBEAT_INTERVAL_SECONDS="$(get_opt heartbeat_interval_seconds)"
  export INVENTORY_EVERY_N_HEARTBEATS="$(get_opt inventory_every_n_heartbeats)"
  export BACKUP_ENABLED="$(get_opt backup_enabled)"
  export BACKUP_EVERY_N_HEARTBEATS="$(get_opt backup_every_n_heartbeats)"
  export BACKUP_ENCRYPTION_KEY="$(get_opt backup_encryption_key)"
  export ADAPTER=supervisor
  export CREDENTIALS_PATH=/data/agent_credentials.json
fi

cd /agent
exec python3 -m titosoft_agent.main
