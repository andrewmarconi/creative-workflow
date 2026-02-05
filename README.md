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

## Getting Started

### 1. Environment Setup

```bash
# Install dependencies
uv sync

# Configure environment
cp .env.example .env  # Edit with your API keys and preferences

# Authenticate with HuggingFace (for Hub models)
huggingface-cli login
```

### 2. Initialize Creative Workspace

```bash
# Setup database and import model configurations
uv run manage.py migrate
uv run manage.py import_presets
uv run manage.py createsuperuser
```

### 3. Launch Creative Studio

```bash
# Start all services for full creative workflow
honcho start
```

| Process | Creative Function |
|---------|-------------------|
| **docker** | Data persistence (PostgreSQL + Valkey) |
| **django** | Creative studio interface at http://localhost:8000/admin/ |
| **worker** | Generative model execution (`default` queue) |
| **enhancement** | Prompt transformation and refinement (`enhancement` queue) |

```bash
# Start minimal setup for configuration
honcho start docker django
```

## Creative Process

### 1. Prompt Creation
- Start with base concepts in the Django admin
- Apply enhancement strategies (rule-based, LLM, or API)
- Iterate through multiple refinement cycles

### 2. Model Experimentation
- Select from multiple diffusion architectures
- Apply architecture-compatible LoRAs
- Adjust generation parameters for different creative outcomes

### 3. Batch Exploration
- Create multiple job variations from a single prompt
- Queue systematic experiments across models and parameters
- Review results and refine creative direction

## Model Palette

| Model | Architecture | Creative Character | Speed | Style Flexibility |
|-------|-------------|-------------------|-------|-------------------|
| Z-Image Turbo | Lumina/S3-DiT | Rapid ideation | ⚡⚡⚡ | Moderate |
| Flux.1-dev | Flux.1 | Balanced creation | ⚡⚡ | High |
| Flux.2 Klein | Flux.1 | Lightweight exploration | ⚡⚡ | High |
| SDXL Turbo | SDXL | Fast prototyping | ⚡⚡⚡ | Moderate |
| Juggernaut XL v9 | SDXL | Photorealistic detail | ⚡ | Very High |
| DreamShaper XL Lightning | SDXL | Stylized speed | ⚡⚡⚡ | High |
| Realistic Vision v5.1 | SD 1.5 | Classic photorealism | ⚡ | Very High |

### Creative Strategies by Model

- **Rapid Iteration**: Z-Image Turbo, SDXL Turbo for quick concept exploration
- **Balanced Creation**: Flux.1-dev, Flux.2 Klein for general creative work
- **Detailed Refinement**: Juggernaut XL, Realistic Vision for final output
- **Stylized Experimentation**: DreamShaper XL Lightning for artistic variations

## Extending the Framework

### Adding New Models

The framework uses a Template Method pattern for easy model extension:

```python
# src/cw/lib/models/yourmodel.py
from cw.lib.models.base import BaseModel

class YourModel(BaseModel):
    def _create_pipeline(self):
        # Return your configured pipeline
        return pipeline
```

1. Add model configuration to `data/presets.json`
2. Implement model class inheriting from `BaseModel`
3. Register in `ModelFactory.create_model()`
4. Sync with `uv run manage.py import_presets`

### Creative LoRA Integration

Add style-specific LoRAs to `data/presets.json`:

```json
{
  "label": "Artistic Style",
  "path": "loras/artistic-style.safetensors",
  "base_architecture": "sdxl",
  "prompt": "in the style of artistic movement",
  "settings": {"strength": 0.8}
}
```

- **Architecture Awareness**: LoRAs automatically filter by compatible base models
- **CivitAI Integration**: Use `air` URNs for automatic community model downloads
- **Creative Stacking**: Combine multiple LoRAs for unique style blends

### Custom Enhancement Strategies

Extend prompt enhancement in `src/cw/lib/prompt_enhancer.py`:

```python
class CreativeEnhancer(BaseEnhancer):
    def enhance(self, prompt: str) -> str:
        # Implement your creative enhancement logic
        return enhanced_prompt
```

## Framework Architecture

```
Generative Creative Lab Framework
├── cw/diffusion/                    # Creative process orchestration
│   ├── models.py                    # Core creative entities
│   ├── admin.py                     # Django Unfold creative studio
│   └── tasks.py                     # Asynchronous creative processes
├── cw/lib/models/                   # Generative model implementations
│   ├── base.py                      # Abstract creative model base
│   ├── mixins.py                    # Shared creative behaviors
│   └── [model implementations]     # Specific diffusion models
├── cw/lib/                          # Creative utilities
│   ├── config.py                    # Configuration management
│   ├── prompt_enhancer.py           # Prompt transformation strategies
│   ├── civitai.py                   # Community model integration
│   └── loras/                       # Style enhancement management
└── data/presets.json               # Creative configuration registry
```

### Design Patterns

- **Template Method**: `BaseModel` provides generation workflow, models implement specifics
- **Strategy Pattern**: Multiple prompt enhancement approaches
- **Factory Pattern**: `ModelFactory` creates appropriate model instances
- **Configuration-Driven**: JSON-based model and style definitions

See [`AGENTS.md`](AGENTS.md) for development guidelines and patterns.

## Environment Requirements

- **Python**: 3.12+ via `uv` package manager
- **Services**: PostgreSQL, Valkey/Redis (Docker Compose provided)
- **GPU**: Apple Silicon (MPS) or CUDA for generation
- **Storage**: ~15-30GB for model cache (`~/.cache/huggingface/`)

## Creative Development

```bash
# Full creative environment
honcho start                              # Launch all creative services

# Configuration management
uv run manage.py migrate                  # Initialize database
uv run manage.py import_presets           # Sync model configurations
uv run manage.py preload_models           # Cache models for faster workflow

# Creative content management
uv run manage.py import_prompts           # Bulk import creative concepts
uv run manage.py export_prompts           # Export creative experiments
```

## Creative Troubleshooting

**Model Loading Issues?**
- Verify HuggingFace authentication for community models
- Check `MODEL_BASE_PATH` in `.env` for local model files
- Ensure model architecture matches available implementations

**Style Enhancement Not Working?**
- Verify LoRA `base_architecture` matches target model
- Check CivitAI AIR URN validity for community downloads
- Confirm LoRA strength settings are appropriate (0.0-1.0)

**Performance Optimization?**
- Use turbo models for rapid iteration (fewer steps)
- Only one model loads at a time (intentional design)
- MPS cache automatically clears after each generation

## Contributing to the Framework

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
