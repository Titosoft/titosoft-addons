# TitoSoft Agent

Conector entre este Home Assistant e a plataforma MSP TitoSoft. **Toda comunicação é outbound** (agente → central); nenhuma porta é aberta na casa.

O que o agente faz:
- Registra a instalação na central (enrollment por token de uso único).
- Envia **heartbeat** periódico (versões, disco, memória, serviços).
- Coleta **inventário** (dispositivos e entidades) via APIs locais do HA.
- Cria **backup full** via Supervisor, **criptografa (AES-256-GCM)** e envia para o storage da central.

## Configuração

| Opção | Descrição |
|---|---|
| `api_base_url` | URL da API central (ex.: `http://192.168.1.10:8000`). |
| `enrollment_token` | Token de uso único gerado no portal MSP (tela da instalação). Válido 24h. |
| `heartbeat_interval_seconds` | Intervalo do heartbeat (padrão 60). |
| `inventory_every_n_heartbeats` | Frequência do inventário (padrão a cada 5 heartbeats). |
| `backup_enabled` | Liga o ciclo de backup. |
| `backup_every_n_heartbeats` | Frequência do backup (1440 ≈ diário com heartbeat de 60s). |
| `backup_encryption_key` | Passphrase da criptografia do backup. **Guarde em cofre — sem ela não há restore.** |

## Passo a passo

1. No **portal MSP**: cliente → site → instalação → **Gerar token de enrollment**.
2. Instale este add-on, aba **Configuração**: preencha `api_base_url`, `enrollment_token` e `backup_encryption_key`.
3. **Iniciar**. Em ~90s a instalação aparece online no portal, com versões reais e inventário.
4. Após o primeiro enrollment, ative **"Iniciar no boot"** e **"Watchdog"** na aba *Informações* do add-on.

As credenciais pós-enrollment ficam em `/data/agent_credentials.json` (persistente, 0600). O token só é usado uma vez; a central guarda apenas o hash.

## Permissões

Roda com `hassio_role: manager` + `homeassistant_api` — necessário para ler o registro de dispositivos/entidades e criar backups via Supervisor. Não altera automações nem configuração do HA.

## Restore de backup

O backup é criptografado no agente antes do upload. Para restaurar, baixe o `.tar.enc` pelo portal e descriptografe com a mesma `backup_encryption_key` (ferramenta `scripts/decrypt-backup.py` da plataforma), depois envie o `.tar` em **Ajustes → Sistema → Backups**.
