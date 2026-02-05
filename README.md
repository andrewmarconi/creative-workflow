![Generative Creative Lab](docs/_static/logo-wide.png)

# Generative Creative Lab

A modular framework for creative development, exploration, and experimentation using generative AI. Built with Django and Celery, this system provides a flexible platform for multi-model diffusion image generation with dynamic model composition, prompt enhancement, and extensible architecture.

## Philosophy

Generative Creative Lab is designed as a **creative laboratory** - not just a tool for generating images, but a framework for exploring the intersection of different AI models, prompting strategies, and creative workflows. It enables rapid experimentation through:

- **Model Modularity**: Mix and match diffusion models, LoRAs, and enhancement strategies
- **Prompt Evolution**: Transform and refine prompts using multiple enhancement approaches
- **Workflow Orchestration**: Queue-based processing for batch experimentation
- **Extensible Architecture**: Easy to add new models, enhancement methods, and creative tools

## Core Capabilities

### Generative Models
- **Diffusion Models**: Z-Image Turbo, Flux.1-dev, Flux.2 Klein, SDXL Turbo, Juggernaut XL, DreamShaper XL Lightning, Realistic Vision v5.1
- **Dynamic LoRA Integration**: Architecture-aware LoRA filtering with CivitAI auto-download
- **Flexible Model Loading**: Local `.safetensors` files or HuggingFace Hub models

### Creative Enhancement
- **Multi-Strategy Prompt Enhancement**: Rule-based transformations, local LLM refinement (Qwen2.5-3B), or Anthropic API enhancement
- **Iterative Workflows**: Chain multiple enhancement steps for prompt evolution
- **Batch Experimentation**: Queue multiple variations for systematic exploration

### Development Framework
- **Template Method Architecture**: Extensible base classes for adding new models and behaviors
- **Configuration-Driven**: JSON-based model and LoRA configuration with database sync
- **Process Isolation**: Separate Celery workers for generation and enhancement tasks

## Documentation

Full documentation, guides, and API reference available at:

**https://andrewmarconi.github.io/generative-creative-lab**

- [Quick Start Guide](https://andrewmarconi.github.io/generative-creative-lab/guides/quickstart.html) - Get up and running
- [System Architecture](https://andrewmarconi.github.io/generative-creative-lab/architecture.html) - Technical overview
- [Adding New Models](https://andrewmarconi.github.io/generative-creative-lab/guides/adding-models.html) - Extend the framework
- [API Reference](https://andrewmarconi.github.io/generative-creative-lab/api/index.html) - Module documentation

## Contributing

This is an open creative framework. Contributions welcome for:
- New model implementations
- Creative enhancement strategies
- Workflow improvements
- Documentation and examples

## License and Non-Commercial Use

Generative Creative Lab is provided as a **creative laboratory** for experimentation with generative AI workflows. It is licensed under the **Generative Creative Lab Non-Commercial License**, which permits use, modification, and distribution **only for Non-Commercial Purposes**.

If you want to use Generative Creative Lab or derivatives of it in any commercial or production setting, you must obtain a separate commercial license from the project owner.

By using or contributing to this repository, you agree to the terms of the Generative Creative Lab Non-Commercial License.

See the [LICENSE](./LICENSE.md) file for full details.


## Citing This Software

If you use this software in your research, please cite it using the following BibTeX entry:

```bibtex
@misc{marconi2026generativecreativelab,
  author       = {Andrew Marconi},
  title        = {Generative Creative Lab},
  year         = {2026},
  howpublished = {\url{https://andrewmarconi.github.io/generative-creative-lab}},
  note         = {Interactive web project},
}
```

> **Marconi, A.** (2026). *Generative Creative Lab* [Interactive web project]. Retrieved from https://andrewmarconi.github.io/generative-creative-lab
