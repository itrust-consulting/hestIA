// Mirrors hestia/domain/rag/graph.py's NODE_TYPE_SPECS/FRAGMENT_TO_TYPE/CONTEXT_FIELDS --
// the six node types the Runner (hestia/handler.py) actually implements, what
// each one reads/writes, and the fixed set of ${...} context fields a workflow
// can reference. Hand-curated the same way llmParamSchemas.ts mirrors backend
// param knowledge -- there is no shared/generated source between the two.

export type NodeTypeSpec = {
  type: string;
  fragment: string;
  label: string;
  inputs: string[];
  outputs: string[];
  // Per-input preferred ${...} context field when an input is switched to
  // "Context field" mode in the inspector -- overrides the generic
  // same-name-as-the-input-key guess (see NodeInspector.svelte's
  // setMode()). Needed wherever an input's name doesn't map 1:1 to a
  // context field of the same name, e.g. EncodeDense's "model" input must
  // default to ${embedding_model}, not ${model} (the chat/generation
  // model) -- that mismatch is what silently sent the wrong model to the
  // embeddings endpoint before.
  contextDefaults?: Record<string, string>;
};

export const NODE_TYPES: NodeTypeSpec[] = [
  {
    type: 'EncodeDense', fragment: 'encode_dense.yaml', label: 'Encode (dense)',
    inputs: ['data', 'model', 'model_kwargs'], outputs: ['vector'],
    contextDefaults: { model: 'embedding_model', model_kwargs: 'embedding_model_kwargs' },
  },
  { type: 'EncodeSparse', fragment: 'encode_sparse.yaml', label: 'Encode (sparse)', inputs: ['data', 'collection'], outputs: ['vector'] },
  {
    type: 'Retrieve', fragment: 'retrieve.yaml', label: 'Retrieve',
    inputs: ['dense', 'sparse', 'collection', 'options'], outputs: ['hits'],
    contextDefaults: { options: 'query_kwargs' },
  },
  { type: 'Augment', fragment: 'augment.yaml', label: 'Augment (RAG prompt)', inputs: ['prompt', 'hits', 'template'], outputs: ['prompt'] },
  {
    type: 'Generate', fragment: 'generate.yaml', label: 'Generate',
    inputs: ['prompt', 'model', 'options'], outputs: ['response'],
    contextDefaults: { options: 'model_kwargs' },
  },
  {
    type: 'Chat', fragment: 'chat.yaml', label: 'Chat',
    inputs: ['history', 'last_user_message', 'model', 'options'], outputs: ['response'],
    contextDefaults: { options: 'model_kwargs' },
  },
];

// TemplatePlanBuilder._build_ctx's fixed set of request fields a node's
// inputs can reference as ${field_name}.
export const CONTEXT_FIELDS = [
  'prompt', 'history', 'last_user_message', 'model', 'model_kwargs', 'collection', 'query_kwargs',
  'embedding_model', 'embedding_model_kwargs',
];
