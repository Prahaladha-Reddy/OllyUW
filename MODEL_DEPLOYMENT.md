# Model Choice and Deployment Notes

This note explains which models were chosen for OllyUW, why they fit the
assignment, and how the open-source model path was deployed.

## Assignment Framing

The assignment asks for two assistants:

- one using an open-source model
- one using a frontier model

The project maps that requirement onto a real underwriting workflow. OllyUW is
not only testing generic chat quality; it is testing whether a model can read
large insurance submission packages, preserve citations, avoid unsupported
claims, resist unsafe instructions, and produce useful underwriting analysis.

## Models Chosen

### Open-source path: Gemma 4 26B-A4B

The open-source model path uses:

```text
google/gemma-4-26B-A4B-it
```

In the Modal deployment scripts, the served model name is:

```text
google/gemma-4-26B-A4B-it
```

The underlying weights currently used by the vLLM server are:

```text
RedHatAI/gemma-4-26B-A4B-it-FP8-Dynamic
```

Gemma 4 26B-A4B was chosen because it is large enough to handle complex
underwriting reasoning, but still practical to deploy on a single rented GPU.
For this project, that balance matters more than leaderboard performance alone:
the model needs long-context document reading, instruction following, structured
output, and reasonable cost.

### Frontier path: DeepSeek

The frontier comparison path uses DeepSeek through an OpenAI-compatible API.
This gives the eval framework a second model family to compare against the
open-source Gemma deployment on:

- hallucination and citation grounding
- bias behavior
- content safety and refusal behavior
- underwriting memo quality

The backend smoke-test script supports this provider as:

```powershell
uv run --project backend python backend/tests/test_inference.py --provider deepseek
```

## Deployment Platform

The open-source model is deployed on Modal using vLLM. Modal was chosen because
it gives us:

- on-demand GPU hosting
- repeatable Python deployment scripts
- persistent cache volumes for Hugging Face and vLLM artifacts
- a simple web server surface for exposing vLLM's OpenAI-compatible API

The deployment files are:

```text
infrastructure/modal/deploy_gemma_standard.py
infrastructure/modal/deploy_gemma_turboquant.py
```

Both deployments use:

```text
GPU: L40S
vLLM port: 8000
served model name: google/gemma-4-26B-A4B-it
weights: RedHatAI/gemma-4-26B-A4B-it-FP8-Dynamic
```

Both expose the model through Modal's web server wrapper:

```python
@modal.web_server(port=VLLM_PORT, startup_timeout=10 * MINUTES)
```

This gives the rest of the application an OpenAI-compatible base URL. The
backend then calls it through LangChain's `ChatOpenAI` client.

## Standard Deployment

The standard deployment is defined in:

```text
infrastructure/modal/deploy_gemma_standard.py
```

This path was our initial working L40S deployment. In practice, although the
server was configured for `131_072` tokens, the usable application-level context
budget was about 120k tokens after accounting for prompt, chat template, and
runtime overhead.

Deploy it with:

```powershell
modal deploy infrastructure/modal/deploy_gemma_standard.py
```


## TurboQuant KV Cache Deployment

The TurboQuant deployment is defined in:

```text
infrastructure/modal/deploy_gemma_turboquant.py
```

The important change was using KV cache compression for the long-context path.
Before this optimization, the L40S deployment could support roughly a 120k-token
usable context window. After applying the compressed KV-cache path, the same L40S
class deployment reached roughly a 253k-token usable context window.

## Why the Longer Context Matters

OllyUW's target workload is underwriting an AI-agent insurance submission. Real
submission packages can include:

- SOC 2 reports
- red-team reports
- system prompts
- tool schemas
- incident logs
- HITL approval logs
- architecture notes
- privacy and legal documents
- evaluation reports

A 120k-token context window is useful, but it still forces more aggressive
chunking and summarization. The approximately 253k-token context window lets the
model inspect much larger evidence bundles in one pass, which improves the core
product behavior:

- fewer dropped source details
- better cross-document inconsistency checks
- stronger citation grounding
- less dependence on early summarization
- better underwriting memo quality
