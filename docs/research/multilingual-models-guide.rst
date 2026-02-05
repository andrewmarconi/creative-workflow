Multilingual Small Language Models Adaptation
=============================================

Executive Summary
-----------------

Some models' instruction-following issues are a known limitation of the 3B parameter size. For TV script cultural adaptation work within 8GB VRAM constraints, **upgrading to Qwen2.5-7B-Instruct with Q4 quantization (~4GB VRAM)** is the most practical solution for most languages. However, optimal model selection varies significantly by target language—this guide provides ISO 639 code mappings to recommended models.


Why Qwen2.5-3B-Instruct May Be Underperforming
----------------------------------------------

The 3B parameter models have limited capacity for complex creative tasks requiring nuanced instruction following [7]_ [4]_. Reported issues include:

- Difficulty maintaining system prompt consistency across long generations
- Weaker performance on creative writing tasks compared to reasoning benchmarks
- Instruction adherence degrades with complex multi-step prompts [49]_


Model Comparison for 8GB VRAM
-----------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 10 10 15 20 20

   * - Model
     - Params
     - VRAM (Q4)
     - Languages
     - Instruction Following
     - Creative/Adaptation
   * - **Qwen2.5-7B-Instruct**
     - 7B
     - ~4GB
     - 29+
     - Very Good
     - Good
   * - **Mistral-7B-v0.3**
     - 7B
     - ~4GB
     - ~10 focus
     - Good
     - Limited for non-European
   * - **Aya-Expanse-8B**
     - 8B
     - ~5GB
     - 23
     - Very Good
     - Good
   * - **Gemma-2-9B**
     - 9B
     - ~5-6GB
     - Variable
     - Very Good
     - Limited
   * - **Phi-3.5-mini**
     - 3.8B
     - ~2.5GB
     - 23
     - Good
     - Moderate
   * - Llama-3.2-3B
     - 3B
     - ~2GB
     - 8 official
     - Good
     - Limited
   * - Qwen2.5-3B (current)
     - 3B
     - ~2GB
     - 29+
     - Good
     - Moderate


Mistral-7B-Instruct-v0.3: Strengths and Limitations
---------------------------------------------------

Mistral-7B-v0.3 has an extended 32,768 token vocabulary and improved function calling support [14]_ [2]_. However, its multilingual performance is uneven:

**Strong Languages:**

- German (excellent with community fine-tunes like EM German Leo Mistral) [27]_
- French, Spanish, Italian, Portuguese
- Malay (Malaysian Mistral achieves 65.3% on grammar tests, outperforming GPT-3.5) [16]_

**Weak Languages:**

- Japanese (produces mixed Japanese/English output) [24]_
- Chinese, Korean (significantly below Qwen family)
- Most non-European languages

Mistral is **not recommended** for Asian language script adaptation without extensive fine-tuning [24]_.


Recommended Models by Language Family
-------------------------------------

East Asian Languages
~~~~~~~~~~~~~~~~~~~~

For Chinese, Japanese, Korean, and Vietnamese, the **Qwen family dominates**. Qwen2.5 models were trained on extensive CJK data with multilingual benchmarks showing 76-80% MMLU scores for Japanese and 60% for Korean [10]_ [57]_.

European Languages
~~~~~~~~~~~~~~~~~~

**Phi-3.5-mini** showed 25-50% improvement in Arabic, Dutch, Finnish, Polish, Thai, and Ukrainian over Phi-3-mini [75]_. For German specifically, Mistral with continued pretraining produces output quality previously requiring 70B models [27]_.

South/Southeast Asian Languages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Llama-3.2-3B** officially supports Hindi, Thai, Portuguese, Spanish, German, French, Italian, and English [26]_ [29]_. For broader coverage, **Aya-Expanse-8B** covers 23 languages including Bengali, Hindi, Thai, Vietnamese, Indonesian, and Filipino [36]_.

Low-Resource Languages
~~~~~~~~~~~~~~~~~~~~~~

**Gemma-2-9B** is the first open model with coherent Slovenian and Uzbek support [22]_. For very low-resource languages, **NLLB-200-1.3B** (pure translation, 200 languages) or **MADLAD-400-3B-MT** (419 languages) are the only viable options [42]_ [45]_.


ISO 639 Language Code → Recommended Model Mapping
-------------------------------------------------

High-Resource Languages
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 15 35 40

   * - ISO Code
     - Language
     - Primary Model
     - Alternatives
   * - ``en``
     - English
     - Qwen2.5-7B-Instruct-Q4
     - Gemma-2-9B-Q4, Phi-3.5-mini
   * - ``zh``
     - Chinese
     - Qwen2.5-7B-Instruct-Q4
     - Qwen2.5-3B-Instruct
   * - ``es``
     - Spanish
     - Qwen2.5-7B-Instruct-Q4
     - Mistral-7B-v0.3-Q4, Aya-Expanse-8B-Q4
   * - ``fr``
     - French
     - Qwen2.5-7B-Instruct-Q4
     - Mistral-7B-v0.3-Q4, Aya-Expanse-8B-Q4
   * - ``de``
     - German
     - Mistral-7B-v0.3-Q4
     - Qwen2.5-7B-Instruct-Q4, Llama-3.2-3B
   * - ``pt``
     - Portuguese
     - Qwen2.5-7B-Instruct-Q4
     - Llama-3.2-3B, Aya-Expanse-8B-Q4
   * - ``it``
     - Italian
     - Qwen2.5-7B-Instruct-Q4
     - Gemma-2-9B-Q4, Llama-3.2-3B
   * - ``ru``
     - Russian
     - Qwen2.5-7B-Instruct-Q4
     - Gemma-2-9B-Q4, Aya-Expanse-8B-Q4
   * - ``ja``
     - Japanese
     - Qwen2.5-7B-Instruct-Q4
     - Aya-Expanse-8B-Q4
   * - ``ko``
     - Korean
     - Qwen2.5-7B-Instruct-Q4
     - Aya-Expanse-8B-Q4

Medium-Resource Languages
~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 15 35 40

   * - ISO Code
     - Language
     - Primary Model
     - Notes
   * - ``ar``
     - Arabic
     - Qwen2.5-7B-Instruct-Q4
     - Phi-3.5 also improved significantly
   * - ``hi``
     - Hindi
     - Llama-3.2-3B
     - Officially supported
   * - ``th``
     - Thai
     - Llama-3.2-3B
     - Phi-3.5 shows 25-50% improvement
   * - ``vi``
     - Vietnamese
     - Qwen2.5-7B-Instruct-Q4
     - Good Qwen coverage
   * - ``tr``
     - Turkish
     - Qwen2.5-7B-Instruct-Q4
     - Strong MMLU performance
   * - ``pl``
     - Polish
     - Phi-3.5-mini
     - Major improvement over Phi-3
   * - ``nl``
     - Dutch
     - Phi-3.5-mini
     - 25-50% improvement
   * - ``uk``
     - Ukrainian
     - Phi-3.5-mini
     - Major improvement
   * - ``id``
     - Indonesian
     - Qwen2.5-7B-Instruct-Q4
     - Good coverage
   * - ``ms``
     - Malay
     - Mistral-7B-v0.3-Q4 (fine-tuned)
     - Malaysian Mistral available

Nordic & Central European Languages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 15 35 40

   * - ISO Code
     - Language
     - Primary Model
     - Notes
   * - ``sv``
     - Swedish
     - Phi-3.5-mini
     - Nordic language support
   * - ``da``
     - Danish
     - Phi-3.5-mini
     - Covered in training
   * - ``fi``
     - Finnish
     - Phi-3.5-mini
     - Major improvement
   * - ``no``
     - Norwegian
     - Phi-3.5-mini
     - Nordic support
   * - ``cs``
     - Czech
     - Phi-3.5-mini
     - Covered in training
   * - ``hu``
     - Hungarian
     - Phi-3.5-mini
     - Covered in training
   * - ``he``
     - Hebrew
     - Phi-3.5-mini
     - Covered in training

Lower-Resource Languages (Creative Adaptation Limited)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 15 35 40

   * - ISO Code
     - Language
     - Primary Model
     - Notes
   * - ``bn``
     - Bengali
     - Aya-Expanse-8B-Q4
     - Limited creative support
   * - ``fa``
     - Persian
     - Aya-Expanse-8B-Q4
     - Aya covers Persian
   * - ``ur``
     - Urdu
     - Aya-Expanse-8B-Q4
     - Limited support
   * - ``sl``
     - Slovenian
     - Gemma-2-9B-Q4
     - First coherent open model
   * - ``uz``
     - Uzbek
     - Gemma-2-9B-Q4
     - First usable open model
   * - ``km``
     - Khmer
     - Aya-Expanse-8B-Q4 + NLLB-200
     - Hybrid approach needed
   * - ``lo``
     - Lao
     - Aya-Expanse-8B-Q4 + NLLB-200
     - Hybrid approach needed
   * - ``my``
     - Burmese
     - Aya-Expanse-8B-Q4 + NLLB-200
     - Hybrid approach needed
   * - ``tl``
     - Tagalog
     - Aya-Expanse-8B-Q4
     - Limited general support
   * - ``sw``
     - Swahili
     - Gemma-2-9B-Q4
     - Fine-tuned versions excel


Specialized Translation Models (No Creative Adaptation)
-------------------------------------------------------

For pure translation without cultural adaptation, these dedicated models offer superior language coverage:

.. list-table::
   :header-rows: 1
   :widths: 30 15 15 40

   * - Model
     - Languages
     - VRAM
     - Use Case
   * - **NLLB-200-Distilled-1.3B**
     - 200
     - ~1GB
     - Broadest coverage, low-resource focus [42]_
   * - **MADLAD-400-3B-MT**
     - 419
     - ~2GB
     - Maximum language coverage, research-grade [45]_
   * - **GemmaX2-28-2B**
     - 28
     - ~1.5GB
     - Competitive with GPT-4 on translation [17]_ [76]_
   * - **TranslateGemma-4B**
     - 55
     - ~2.5GB
     - Newest, multimodal capable [85]_

These models cannot do creative adaptation—they translate but don't understand cultural context for script localization.


Recommended Workflow for TV Script Adaptation
---------------------------------------------

Option 1: Single Model Approach (Simplest)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use **Qwen2.5-7B-Instruct-Q4** (~4GB VRAM) for most languages. It covers 29+ languages with good instruction following and handles creative writing tasks well [7]_ [66]_.

Option 2: Multi-Model Pipeline (Best Quality)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Translation Pass:** Use specialized model (GemmaX2-28-2B or NLLB-200) for accurate linguistic translation
2. **Cultural Adaptation Pass:** Use general model (Qwen2.5-7B-Q4 or Aya-Expanse-8B-Q4) for cultural localization
3. **Review Pass:** Same general model for consistency and instruction following

Option 3: Language-Specific Routing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Deploy different quantized models based on target language:

- Load Qwen2.5-7B-Q4 for CJK languages
- Load Mistral-7B-Q4 for Western European
- Load Phi-3.5-mini for Nordic/Central European
- Load Aya-Expanse-8B-Q4 for South Asian

This maximizes quality per language but requires more complex orchestration.


Key Takeaways
-------------

1. **Upgrade from 3B to 7B/8B:** The instruction-following issues you're experiencing are largely solved by moving to larger models with Q4 quantization [3]_ [50]_

2. **Mistral-7B is NOT universal:** It excels at European languages but struggles with Asian languages—not recommended for Japanese, Chinese, or Korean script work [24]_

3. **Qwen2.5-7B-Instruct-Q4 is the best general choice:** Covers 29+ languages, excellent instruction following, fits 8GB VRAM, and handles creative tasks well [57]_ [66]_

4. **For low-resource languages:** Use Aya-Expanse-8B-Q4 or Gemma-2-9B-Q3 for creative tasks, supplemented by NLLB-200 for translation accuracy [36]_ [22]_

5. **Quantization is key:** At Q4_K_M quantization, 7-9B models fit in 8GB VRAM with ~95% performance retention [3]_ [53]_


References
----------

.. [2] `What are the key features of the Mistral-7b-instruct-v0.3 model? <https://www.facebook.com/groups/DeepNetGroup/posts/2200282560364614/>`_ - Multilingual Capabilities: Mixtral shows significant performance improvement in multilingual understanding...

.. [3] `Best Local LLMs for 8GB VRAM: Complete 2025 Performance Guide <https://localllm.in/blog/best-local-llms-8gb-vram-2025>`_ - Comprehensive 2025 analysis of top-performing local LLMs optimized for 8GB VRAM systems...

.. [4] `Qwen2.5-3B: Specifications and GPU VRAM Requirements <https://apxml.com/models/qwen2-5-3b>`_ - The model demonstrates proficiency in instruction following and the generation of structured outputs...

.. [7] `Qwen/Qwen2.5-3B-Instruct - Hugging Face <https://huggingface.co/Qwen/Qwen2.5-3B-Instruct>`_ - Long-context Support up to 128K tokens and can generate up to 8K tokens. Multilingual support for over 29 languages...

.. [10] `Qwen2.5-LLM: Extending the Boundary of LLMs - Alibaba Cloud <https://www.alibabacloud.com/blog/601786>`_ - Details of the latest Qwen2.5 series language models...

.. [14] `mistralai/Mistral-7B-Instruct-v0.3 - Hugging Face <https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3>`_ - The Mistral 7B Instruct model demonstration that the base model can be easily fine-tuned...

.. [16] `Mistral 7B: Efficient Open-Source LLM - Emergent Mind <https://www.emergentmind.com/topics/mistral-7b-language-model>`_ - Mistral 7B is an open-source, decoder-only language model with 7 billion parameters...

.. [17] `Gemma-2X 9b models achieve SOTA in 28 languages - LinkedIn <https://www.linkedin.com/posts/vijaysaraswat_more-evidence-for-thousand-points-of-light-activity-7299034228011225088-Ku_N>`_ - Gemma-2X 9b models provides competitive performance for translation...

.. [22] `Evaluation of Gemma 2 9B and 27B on LMSYS Chatbot Arena - Reddit <https://www.reddit.com/r/LocalLLaMA/comments/1dps391/evaluation_of_gemma_2_9b_and_27b_on_lmsys_chatbot/>`_ - Very usable translations, better than any existing translation tools...

.. [24] `A Performance Showdown Across NLP, Code, and Multilingual Tasks <https://rogue-scholar.org/records/9y2zc-jfe16>`_ - Performance benchmarks of the Mistral 7B model compared to others...

.. [26] `llama-3.2-3b-instruct Model by Meta - NVIDIA NIM APIs <https://build.nvidia.com/meta/llama-3.2-3b-instruct/modelcard>`_ - Supported Languages: English, German, French, Italian, Portuguese, Hindi, Spanish, and Thai...

.. [27] `EM German - Mistral + Continuous Pretraining + high-quality Finetune - Reddit <https://www.reddit.com/r/LocalLLaMA/comments/174i0vh/em_german_mistral_continous_pretraining/>`_ - Unprecedented non-English performance...

.. [29] `meta-llama/Llama-3.2-3B - Hugging Face <https://huggingface.co/meta-llama/Llama-3.2-3B>`_ - Supported Languages: English, German, French, Italian, Portuguese, Hindi, Spanish, and Thai...

.. [36] `Aya Expanse: Combining Research Breakthroughs for a New Multilingual Model - arXiv <https://arxiv.org/abs/2412.04261>`_ - The Aya Expanse model family, a new generation of 8B and 32B parameter multilingual language models...

.. [42] `200 languages within a single AI model: A breakthrough in high-quality translation - Meta AI <https://ai.meta.com/blog/nllb-200-high-quality-machine-translation/>`_ - NLLB-200, which translates 200 different languages with state-of-the-art quality...

.. [45] `Madlad400 3b Mt - Dataloop <https://dataloop.ai/library/model/jbochi_madlad400-3b-mt/>`_ - Powerful multilingual machine translation model that can handle over 400 languages...

.. [49] `Qwen2.5 Bugs & Issues + fixes - Reddit <https://www.reddit.com/r/LocalLLaMA/comments/1fnvlla/qwen25_bugs_issues_fixes_colab_finetuning_notebook/>`_ - Qwen 2.5 support in Unsloth for 2x faster & 70% less VRAM finetuning...

.. [50] `8B Q7 or 7B Q8 on 8GB VRAM? - Reddit <https://www.reddit.com/r/LocalLLaMA/comments/1jdsl15/8b_q7_or_7b_q8_on_8gb_vram/>`_ - Q7 and Q8 are nearly undistinguishable from FP16 quality-wise...

.. [53] `10 Best Small Local LLMs to Try Out (< 8GB) <https://apidog.com/blog/small-local-llm/>`_ - Quantization compresses model weights to use fewer bits...

.. [57] `Qwen2.5: A Party of Foundation Models! | Qwen <https://qwenlm.github.io/blog/qwen2.5/>`_ - Multilingual support for over 29 languages, including Chinese, English, French, Spanish...

.. [66] `Qwen/Qwen2.5-7B-Instruct - Hugging Face <https://huggingface.co/Qwen/Qwen2.5-7B-Instruct>`_ - Long-context Support up to 128K tokens and can generate up to 8K tokens. Multilingual support...

.. [75] `Discover the New Multi-Lingual, High-Quality Phi-3.5 SLMs - Microsoft <https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/discover-the-new-multi-lingual-high-quality-phi-3-5-slms/4225280>`_ - Phi-3.5-mini shows significant improvement over Phi-3-mini on multi-lingual support...

.. [76] `GemmaX: Multilingual Translator based on Gemma Open Models - GitHub <https://github.com/xiaomi-research/gemmax>`_ - GemmaX2 models support 28 languages...

.. [85] `TranslateGemma: A new suite of open translation models - Google Blog <https://blog.google/innovation-and-ai/technology/developers-tools/translategemma/>`_ - TranslateGemma is a new open translation model built on Gemma 3...
