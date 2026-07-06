# TitoSoft Add-ons para Home Assistant

Repositório **público** de add-ons da TitoSoft para instalação via interface do Home Assistant.

## Como adicionar este repositório

1. No Home Assistant: **Ajustes → Add-ons → Loja de add-ons**.
2. Menu **⋮** (canto superior direito) → **Repositórios**.
3. Cole a URL deste repositório e clique em **Adicionar**:
   ```
   https://github.com/Titosoft/titosoft-addons
   ```
4. Feche. O add-on **TitoSoft Agent** aparece na loja, seção *TitoSoft Add-ons*.

## Add-ons disponíveis

| Add-on | Descrição |
|---|---|
| [TitoSoft Agent](./titosoft_agent) | Conecta este Home Assistant à plataforma MSP TitoSoft: heartbeat, inventário e backup criptografado. Comunicação sempre outbound; nenhuma porta é aberta na casa. |

## Instalação e uso do agente

Veja [titosoft_agent/DOCS.md](./titosoft_agent/DOCS.md). Resumo:

1. Instale o add-on **TitoSoft Agent** pela loja (após adicionar este repo).
2. No portal MSP, gere um **token de enrollment** para a instalação.
3. Na aba *Configuração* do add-on, preencha `api_base_url`, `enrollment_token` e `backup_encryption_key`.
4. Inicie. Em ~90s a instalação aparece online no portal.

## Desenvolvimento

O código do agente é aberto (roda na casa do cliente). Testes:

```bash
cd titosoft_agent
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

## Licença

Proprietário TitoSoft. O código do agente é disponibilizado para transparência e instalação; a plataforma central (API/portal) é privada.
