Research Notes
==============

Background research and reference materials that informed design decisions.

Multilingual LLM Model Selection
---------------------------------

The adaptation pipeline requires LLM models that can generate culturally-appropriate text in the target language. Model selection is driven by language coverage, structured generation support, and memory footprint.

Evaluated Models
^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Model
     - Parameters
     - Notes
   * - Qwen 2.5 7B Instruct
     - 7B
     - Strong multilingual (29+ languages), best for CJK. Default primary model.
   * - Qwen 2.5 3B Instruct
     - 3B
     - Lighter variant for prompt enhancement. Used by HFPromptEnhancer.
   * - CohereForAI Aya Expanse 8B
     - 8B
     - 23 languages, strong for African and South Asian languages.
   * - Mistral Nemo Instruct 12B
     - 12B
     - European language specialist, good for Romance/Germanic.
   * - Google Gemma-2 9B
     - 9B
     - Broad coverage, good at instruction following.
   * - Meta Llama 3.1 8B
     - 8B
     - Strong English, adequate multilingual. Alternative model.

Selection Criteria
^^^^^^^^^^^^^^^^^^

1. **Language coverage** --- must handle the target language well, especially for non-Latin scripts
2. **Structured generation** --- must work with Outlines library for Pydantic schema constraints
3. **4-bit quantization** --- must run in ~6 GB VRAM when quantized
4. **Chat template** --- must have a proper chat template for system/user message formatting

The ``primary_model`` field on each Language record maps to the best LLM for that language. Alternative models are listed for fallback.

Adaptation Pipeline Design
--------------------------

The 7-node pipeline was designed to separate concerns and enable independent evaluation of each quality dimension.

Why Separate Evaluation Gates
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Early prototypes used a single LLM call for adaptation + evaluation. This failed because:

- A single prompt could not reliably check format compliance, cultural sensitivity, concept fidelity, and brand consistency simultaneously
- Failures were hard to diagnose --- which dimension caused the rejection?
- Retry logic could not target specific issues

The current design uses four specialized evaluation nodes, each with its own prompt template and Pydantic schema. When an evaluation fails, the specific failure reason is recorded and the writer node receives targeted feedback for revision.

Retry Budget
^^^^^^^^^^^^

Each evaluation gate allows up to 3 retries. This budget was chosen empirically:

- 1 retry catches most formatting issues (wrong language in descriptions, missing translations)
- 2 retries handle most cultural adjustments
- 3 retries is a reasonable maximum before the pipeline should stop and surface the issue for human review

Structured Generation
^^^^^^^^^^^^^^^^^^^^^

The pipeline uses the `Outlines <https://github.com/dottxt-org/outlines>`_ library to constrain LLM output to Pydantic schemas. This eliminates JSON parsing errors and ensures each node produces well-formed output.

Trade-off: structured generation is slower than free-form generation and requires models that handle constrained decoding well. Larger models (7B+) are significantly more reliable than 3B models for this purpose.

Video Upload Security
---------------------

Video file uploads are validated through 5 layers of security before processing.

Threat Model
^^^^^^^^^^^^

Video files can carry:

- **Oversized payloads** --- denial of service via memory/disk exhaustion
- **Extension spoofing** --- ``.mp4`` extension with non-video content
- **MIME type mismatches** --- content that doesn't match declared type
- **Malformed headers** --- files with invalid or missing magic bytes
- **Path traversal** --- filenames with ``../`` or special characters

Validation Chain
^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Validator
     - What It Checks
   * - ``FileSizeValidator``
     - File does not exceed ``VIDEO_MAX_UPLOAD_SIZE_BYTES`` (default 500 MB)
   * - ``FileExtensionValidator``
     - Extension is in allowlist (``.mp4``, ``.mov``, ``.avi``, ``.mkv``, ``.webm``)
   * - ``MimeTypeValidator``
     - Content MIME type (via ``libmagic``) matches allowlist
   * - ``FileHeaderValidator``
     - First bytes match known video container magic numbers
   * - ``FilenameSanitizer``
     - Strips path components, normalizes Unicode, removes special characters

All validators run before the file is passed to the video analysis pipeline. Validation is configured via Django settings and can be adjusted per deployment.

Design Decision: the composite ``VideoFileValidator`` runs all 5 checks and reports all failures at once (rather than fail-fast), so operators see the complete list of issues.

Model Memory Management
-----------------------

GPU VRAM is the primary constraint. The system manages memory through:

Sequential Execution
^^^^^^^^^^^^^^^^^^^^

The Celery solo pool ensures only one task runs at a time. Combined with module-level model caching, this means:

- Only one diffusion model is loaded at a time
- Switching models evicts the previous one and frees VRAM
- Prompt enhancement and pipeline LLMs are evicted before image generation

Eviction Strategy
^^^^^^^^^^^^^^^^^

Before image generation:

1. ``_evict_enhancer()`` --- clears cached HFPromptEnhancer (Qwen 3B)
2. ``_evict_pipeline_model()`` --- clears PipelineModelLoader singleton (Qwen 7B)
3. ``gc.collect()`` + ``torch.cuda.empty_cache()`` / ``torch.mps.empty_cache()``

This ensures the full VRAM budget is available for the diffusion model.

Quantization
^^^^^^^^^^^^

- LLM models support ``load_in_4bit`` for ~4x memory reduction (via ``bitsandbytes``)
- Diffusion models support ``load_in_8bit`` (Qwen-Image only)
- All diffusion models use ``bfloat16`` or ``float16`` precision
- VAE is kept in ``float32`` on Apple Silicon (MPS) to avoid precision issues
