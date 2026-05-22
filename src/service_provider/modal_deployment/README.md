# Modal Gemma 4 Serving

This folder has two Modal deployments for the same Gemma 4 vLLM server:

- `deploy_gemma4_standard.py`: A10G + AWQ INT4, no TurboQuant KV-cache setting.
- `deploy_gemma4_turboquant.py`: same server with `kv_cache_dtype="turboquant_k8v4"`.

Both expose an OpenAI-compatible vLLM endpoint. LangChain can talk to them through
`ChatOpenAI` by setting `base_url` to the deployed Modal URL plus `/v1`.

## One-time Modal setup

```powershell
uv run modal setup
```

## Deploy standard endpoint

```powershell
uv run modal deploy src/service_provider/modal/deploy_gemma4_standard.py
```

Modal will print a URL like:

```text
https://<workspace>--ollyuw-vllm-standard-serve.modal.run
```

Put that in `.env`:

```text
MODAL_STANDARD_BASE_URL=https://<workspace>--ollyuw-vllm-standard-serve.modal.run
```

## Deploy TurboQuant endpoint

```powershell
uv run modal deploy src/service_provider/modal/deploy_gemma4_turboquant.py
```

Modal will print a URL like:

```text
https://<workspace>--ollyuw-vllm-turboquant-serve.modal.run
```

Put that in `.env`:

```text
MODAL_TURBO_BASE_URL=https://<workspace>--ollyuw-vllm-turboquant-serve.modal.run
```

## Test with LangChain

```powershell
uv run python src/service_provider/test_inference.py --provider modal-standard
uv run python src/service_provider/test_inference.py --provider modal-turbo
uv run python src/service_provider/test_inference.py --provider deepseek
```

For a simple terminal chat loop:

```powershell
uv run python src/service_provider/test_inference.py --provider modal-standard --chat
```

## How LangChain connects

The Modal deployments run vLLM's OpenAI-compatible server, so the client code is
the same shape as DeepSeek:

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="google/gemma-4-26B-A4B-it",
    base_url="https://<workspace>--ollyuw-vllm-standard-serve.modal.run/v1",
    api_key="unused",
    temperature=0,
)

print(llm.invoke("hello").content)
```

DeepSeek uses its own OpenAI-compatible base URL:

```python
llm = ChatOpenAI(
    model="deepseek-v4-flash",
    base_url="https://api.deepseek.com",
    api_key=os.environ["DEEPSEEK_API_KEY"],
    temperature=0,
)
```
