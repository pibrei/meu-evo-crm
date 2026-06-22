# Evo KB Search (RAG)

Serviço leve de RAG para o agente do Evo CRM. Faz busca vetorial sobre o
**pgvector que já roda no stack** (serviço `postgres`) e expõe um endpoint
`/search` que o agente consome como **HTTP custom tool**.

```
docs (.md/.txt) ──ingest──►  chunk + embedding  ──►  pgvector (tabela kb_chunks)
                                                          ▲
agente Evo ──HTTP custom tool /search──► embedding da query ──► top-k chunks
```

## Endpoints

| Método | Rota | Uso |
|---|---|---|
| `GET` | `/health` | healthcheck |
| `POST` | `/search` | `{ "query": "...", "top_k": 5, "source": null }` → `{ "results": [...] }` |
| `POST` | `/ingest` | `{ "documents": [{ "content", "source", "metadata" }], "replace": true }` |

Todas as rotas (menos `/health`) exigem o header **`X-API-Key: <KB_API_KEY>`**.

## Variáveis de ambiente (configurar no Coolify)

| Var | Default | Descrição |
|---|---|---|
| `KB_API_KEY` | — | chave que o agente envia no header `X-API-Key` (gere uma forte) |
| `EMBED_BASE_URL` | `https://api.openai.com/v1` | endpoint OpenAI-compatible de embeddings |
| `EMBED_API_KEY` | — | chave do provider de embeddings |
| `EMBED_MODEL` | `text-embedding-3-small` | modelo de embedding |
| `EMBED_DIM` | `1536` | dimensão do vetor (deve casar com o modelo) |
| `EMBED_QUERY_PREFIX` / `EMBED_DOC_PREFIX` | vazio | prefixos (use para modelos da família e5) |
| `POSTGRES_*` | herda do stack | conexão ao `postgres` (pgvector) |

> ⚠️ `EMBED_DIM` é fixado na criação da tabela `kb_chunks`. Se trocar de modelo
> para outra dimensão depois, recrie a tabela (`DROP TABLE kb_chunks`) e reingira.

### Opções de embeddings (do mais barato ao mais simples)

- **OpenAI `text-embedding-3-small`** (default): ótimo PT-BR, ~US$0,02/1M tokens
  (toda a sua base custa centavos; por consulta é desprezível). `EMBED_DIM=1536`.
- **Local / self-host (zero custo por consulta):** suba um servidor de embeddings
  OpenAI-compatible (ex.: **Ollama** com `nomic-embed-text`) e aponte
  `EMBED_BASE_URL=http://ollama:11434/v1`, `EMBED_MODEL=nomic-embed-text`,
  `EMBED_DIM=768`. Nenhuma mudança de código.
- **Jina / Gemini / Voyage:** qualquer provider com API OpenAI-compatible de embeddings.

## Ingestão dos documentos

Coloque seus procedimentos, troubleshooting, regras de plano, diagnóstico IPTV,
scripts de retenção etc. em arquivos `.md`/`.txt` e rode:

```bash
# a partir da máquina, apontando para o serviço (porta interna 8080)
KB_API_KEY=suachave python ingest.py ./docs --url http://localhost:8080
```

Reingerir o mesmo `source` **substitui** os chunks antigos (idempotente).

## Registrar como HTTP custom tool no agente do Evo

No Evo, ao editar o agente → **Tools → HTTP custom tool**:

- **name:** `buscar_conhecimento`
- **description:** `Busca procedimentos, troubleshooting e regras na base de conhecimento da LCA. Use sempre que precisar de informação técnica/comercial que não seja dado ao vivo do cliente.`
- **method:** `POST`
- **endpoint:** `http://evo_kb_search:8080/search`  *(rede interna do stack)*
- **headers:** `X-API-Key: <KB_API_KEY>`
- **body_params:**
  - `query` → type `string`, required `true`, description `"tema ou pergunta a buscar"`
  - `top_k` → type `number`, required `false`, description `"quantos trechos retornar (padrão 5)"`
- **error_handling:** timeout `15`, retry `1`

O agente passa a chamar essa tool e responder fundamentado nos trechos retornados.
