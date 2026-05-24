// Single source of truth for available LLM backends. The string `id` is
// the wire identifier sent to the backend; the worker maps it to a concrete
// (base_url, api_key, model_name) triple. Add a new provider by adding an
// entry here and a branch in `worker._resolve_llm_config`.

export const MODELS = [
  {
    id: 'modal',
    label: 'Gemma 4',
    sublabel: 'Self-hosted on Modal',
  },
  {
    id: 'deepseek',
    label: 'DeepSeek',
    sublabel: 'Frontier reasoning',
  },
]

export const DEFAULT_MODEL_ID = 'modal'

const BY_ID = Object.fromEntries(MODELS.map((m) => [m.id, m]))

export function getModel(id) {
  return BY_ID[id] ?? BY_ID[DEFAULT_MODEL_ID]
}
