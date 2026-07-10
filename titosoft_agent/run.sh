#!/usr/bin/env sh
# Entrypoint do add-on: carrega o ambiente do container, converte
# /data/options.json em variáveis de ambiente e inicia o agente.
set -e

# s6-overlay (base image do HA) roda o CMD com um ambiente mínimo: as variáveis
# do container — incluindo SUPERVISOR_TOKEN — ficam como arquivos aqui. Sem isto,
# o adapter supervisor falha com "SUPERVISOR_TOKEN ausente". No build standalone
# (python:3.12-slim) a pasta não existe e o bloco é ignorado.
if [ -d /run/s6/container_environment ]; then
  for f in /run/s6/container_environment/*; do
    if [ -f "$f" ]; then
      export "$(basename "$f")=$(cat "$f")"
    fi
  done
fi

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
  export Z2M_MQTT_ENABLED="$(get_opt z2m_mqtt_enabled)"
  export Z2M_MQTT_HOST="$(get_opt z2m_mqtt_host)"
  export Z2M_MQTT_PORT="$(get_opt z2m_mqtt_port)"
  export Z2M_MQTT_USERNAME="$(get_opt z2m_mqtt_username)"
  export Z2M_MQTT_PASSWORD="$(get_opt z2m_mqtt_password)"
  export Z2M_MQTT_BASE_TOPIC="$(get_opt z2m_mqtt_base_topic)"
  export ADAPTER=supervisor
  export CREDENTIALS_PATH=/data/agent_credentials.json
fi

cd /agent
exec python3 -m titosoft_agent.main
