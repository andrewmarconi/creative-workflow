Adaptation Pipeline
===================

.. admonition:: Stub
   :class: warning

   This page is a placeholder. Content to be written.

The multi-agent cultural adaptation system explained.

Planned content:

- LangGraph multi-agent architecture overview
- The 7 pipeline nodes:

  1. Concept extraction (analyzes origin script)
  2. Cultural research (investigates target market)
  3. Script writing (culturally-adapted output)
  4. Format evaluation gate
  5. Cultural evaluation gate
  6. Concept evaluation gate
  7. Brand evaluation gate

- Evaluation gates and retry logic (max 3 retries per gate)
- State flow diagram (Mermaid)
- Model resolution chain: AdUnit override → PipelineSettings → Language primary model
- PipelineModelLoader singleton and per-node LLM selection
- Output artifacts: concept brief, cultural brief, evaluation history, adapted script rows
