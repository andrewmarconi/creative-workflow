# Code Quality Improvement Plan

**Project**: Creative Workflow
**Date**: 2026-02-05
**Scope**: Fix critical complexity issues and establish quality standards

---

## Overview

This plan addresses **3 critical functions** with excessive complexity (17-20) and establishes automated quality tooling to prevent future issues.

**Estimated Time**: 4-6 hours
**Risk Level**: Low (extensive testing after each change)

---

## Phase 1: Baseline & Quick Wins (30 minutes)

### 1.1 Save Current State ✓
- **Action**: Save complete analysis to `docs/code-quality-before.md`
- **Purpose**: Baseline metrics for before/after comparison
- **Time**: 5 minutes

### 1.2 Automated Formatting
- **Action**: Run Black formatter (line-length=100)
  ```bash
  uv run black cw/ lib/ --line-length 100
  ```
- **Impact**: Fixes 53 line-length violations automatically
- **Risk**: None (formatting only)
- **Time**: 5 minutes

### 1.3 Import Organization
- **Action**: Run isort with Black profile
  ```bash
  uv run isort cw/ lib/ --profile black
  ```
- **Impact**: Organizes imports consistently
- **Risk**: None
- **Time**: 5 minutes

### 1.4 Remove Unused Imports
- **Action**: Run autoflake on detected issues
  ```bash
  uv run autoflake --in-place --remove-unused-variables \
    --remove-all-unused-imports cw/ lib/ -r
  ```
- **Impact**: Removes 7 unused imports (F401 violations)
- **Risk**: None (only removes truly unused code)
- **Time**: 5 minutes

### 1.5 Verify Changes
- **Action**: Run flake8 to confirm improvements
  ```bash
  uv run flake8 cw/ lib/ --max-complexity=10 --max-line-length=100 \
    --extend-ignore=E203,W503 --statistics
  ```
- **Expected**: Violations drop from 87 → ~30 (only complexity remains)
- **Time**: 5 minutes

---

## Phase 2: Critical Refactoring (3-4 hours)

### 2.1 Refactor: `generate_images_task` (Complexity: 20 → <10)

**File**: `cw/diffusion/tasks.py:163-410`
**Estimated Time**: 90 minutes

#### Current Problems
- 250 lines, 8+ responsibilities
- Deep nesting (try/except → if/else → for loop → callback)
- LoRA path resolution embedded
- Metadata building mixed with generation

#### Refactoring Strategy

**Step 1**: Extract LoRA path resolution (15 min)
```python
def _resolve_lora_path(lora_model: LoraModel, base_path: Path) -> Path:
    """
    Resolve LoRA file path from model config.

    Handles:
    - Absolute paths
    - Relative paths (resolved against base_path)
    - AIR URNs (CivitAI auto-download)

    Raises:
        RuntimeError: If LoRA has no path and no AIR
    """
    if lora_model.path:
        lora_path_obj = Path(lora_model.path)
        return lora_path_obj if lora_path_obj.is_absolute() \
               else base_path / lora_model.path
    elif lora_model.air:
        _, version_id = parse_air(lora_model.air)
        return base_path / 'loras' / f'civitai_{version_id}.safetensors'
    else:
        raise RuntimeError(f"LoRA '{lora_model.label}' has no path and no AIR")
```

**Step 2**: Extract LoRA configuration builder (10 min)
```python
def _build_lora_config(lora_model: LoraModel, strength: float) -> Dict:
    """Build LoRA config dict for BaseModel.load_lora()."""
    config = {
        'label': lora_model.label,
        'path': lora_model.path,
        'prompt': lora_model.prompt_suffix,
        'negative_prompt': lora_model.negative_prompt_suffix,
        'settings': {'strength': strength}
    }

    if lora_model.clip_skip is not None:
        config['settings']['clip_skip'] = lora_model.clip_skip

    return config
```

**Step 3**: Extract generation parameters builder (10 min)
```python
def _build_generation_params(job: DiffusionJob) -> Dict:
    """Extract generation parameters from job."""
    params = job.get_generation_params()
    return {
        'prompt': params['prompt'],
        'negative_prompt': params.get('negative_prompt'),
        'width': params['width'],
        'height': params['height'],
        'steps': params['steps'],
        'guidance_scale': params['guidance_scale'],
        'seed': params.get('seed'),
        'scheduler': params.get('scheduler'),
    }
```

**Step 4**: Extract metadata builder (15 min)
```python
def _build_generation_metadata(
    job: DiffusionJob,
    images_metadata: List[Dict],
    first_pipeline_meta: Dict
) -> Dict:
    """Build comprehensive generation metadata."""
    return {
        'identifier': job.identifier or None,
        'model': {
            'slug': job.diffusion_model.slug,
            'label': job.diffusion_model.label,
            'path': job.diffusion_model.path,
            'pipeline': job.diffusion_model.pipeline,
            'base_architecture': job.diffusion_model.base_architecture,
        },
        'lora': _build_lora_metadata(job) if job.lora_model else None,
        'prompt': _build_prompt_metadata(job, first_pipeline_meta),
        'parameters': _build_params_metadata(job, first_pipeline_meta),
        'images': images_metadata,
        'generated_at': timezone.now().isoformat(),
    }
```

**Step 5**: Extract image generation loop (20 min)
```python
def _generate_images_batch(
    model: BaseModel,
    gen_params: Dict,
    num_images: int,
    media_dir: Path,
    job: DiffusionJob
) -> Tuple[List[str], List[Dict]]:
    """
    Generate multiple images with progress tracking.

    Returns:
        Tuple of (saved_paths, images_metadata)
    """
    saved_paths = []
    images_metadata = []

    for idx in range(num_images):
        # Randomize seed if not set
        if gen_params.get('seed') is None:
            gen_params['seed'] = random.randint(0, 2**32 - 1)

        logger.info(f"Generating image {idx+1}/{num_images} (seed: {gen_params['seed']})")

        # Generate with progress callback
        callback = _create_progress_callback(gen_params['steps'])
        image, metadata = model.generate(**gen_params, progress_callback=callback)

        # Save image
        filename = _build_filename(job, idx, num_images)
        filepath = media_dir / filename
        image.save(filepath, quality=95)

        # Store results
        rel_path = str(filepath.relative_to(settings.MEDIA_ROOT))
        saved_paths.append(rel_path)
        images_metadata.append({
            'image_index': idx,
            'filename': filename,
            'seed': gen_params['seed'],
            'pipeline_metadata': metadata
        })

    return saved_paths, images_metadata
```

**Step 6**: Simplified main task (20 min)
```python
@shared_task(bind=True, name='cw.diffusion.tasks.generate_images_task')
def generate_images_task(self, job_id):
    """
    Generate images using diffusion models.

    Orchestrates the full generation pipeline:
    1. Load and prepare job
    2. Load model with optional LoRA
    3. Generate images batch
    4. Save results and metadata

    Args:
        job_id: ID of the DiffusionJob to process

    Returns:
        Dict with job results
    """
    job_id = int(job_id)
    job = DiffusionJob.objects.get(id=job_id)

    try:
        # Prepare job
        job.status = 'processing'
        job.started_at = timezone.now()
        job.save()

        # Load model with LoRA
        _evict_enhancer()
        model = _load_model_instance(job.diffusion_model)
        _configure_lora(model, job)

        # Generate images
        gen_params = _build_generation_params(job)
        media_dir = Path(settings.MEDIA_ROOT) / 'diffusion'
        media_dir.mkdir(parents=True, exist_ok=True)

        saved_paths, images_metadata = _generate_images_batch(
            model, gen_params, job.get_generation_params()['num_images'],
            media_dir, job
        )

        # Save results
        job.result_images = saved_paths
        job.generation_metadata = _build_generation_metadata(
            job, images_metadata, images_metadata[0]['pipeline_metadata']
        )
        job.status = 'completed'
        job.completed_at = timezone.now()
        job.save()

        # Cleanup
        if model.current_lora:
            model.unload_lora()

        return {
            'status': 'success',
            'job_id': job_id,
            'images_count': len(saved_paths),
            'paths': saved_paths
        }

    except Exception as e:
        job.status = 'failed'
        job.error_message = str(e)
        job.completed_at = timezone.now()
        job.save()

        return {'status': 'failed', 'job_id': job_id, 'error': str(e)}
```

**Expected Outcome**:
- Complexity: 20 → 4 (main task)
- Helper functions: 4-6 complexity each
- Total lines: Same, but split into ~8 focused functions
- Testability: Much improved (can test each helper independently)

---

### 2.2 Refactor: `refresh_metadata_bulk_action` (Complexity: 20 → <10)

**File**: `cw/diffusion/admin.py:264-356`
**Estimated Time**: 60 minutes

#### Refactoring Strategy

**Step 1**: Extract single LoRA refresh (20 min)
```python
@dataclass
class LoraRefreshResult:
    """Result of refreshing a single LoRA's metadata."""
    lora: LoraModel
    updated: bool = False
    failed: bool = False
    error: Optional[str] = None
    updated_fields: List[str] = field(default_factory=list)

def _refresh_single_lora_metadata(lora: LoraModel, api_key: str) -> LoraRefreshResult:
    """
    Refresh metadata from CivitAI for a single LoRA.

    Returns:
        LoraRefreshResult with outcome
    """
    result = LoraRefreshResult(lora=lora)

    try:
        model_id, version_id = parse_air(lora.air)
        raw_metadata = fetch_model_version_metadata(version_id, api_key)
        extracted = extract_lora_metadata(raw_metadata)

        result.updated_fields = _apply_metadata_updates(lora, extracted)

        if result.updated_fields:
            lora.save()
            result.updated = True

    except Exception as e:
        result.failed = True
        result.error = str(e)

    return result
```

**Step 2**: Extract metadata application (15 min)
```python
def _apply_metadata_updates(lora: LoraModel, metadata: Dict) -> List[str]:
    """
    Apply fetched metadata to LoRA model.

    Returns:
        List of field names that were updated
    """
    updated_fields = []

    # Update label if auto-generated
    if _should_update_label(lora, metadata):
        lora.label = metadata['label']
        updated_fields.append('label')

    # Update architecture
    if metadata.get('base_architecture') != lora.base_architecture:
        lora.base_architecture = metadata['base_architecture']
        updated_fields.append('base_architecture')

    # Update prompt suffixes
    if metadata.get('prompt_suffix') != lora.prompt_suffix:
        lora.prompt_suffix = metadata['prompt_suffix']
        updated_fields.append('trigger words')

    # Update negative prompt
    if metadata.get('negative_prompt_suffix') != lora.negative_prompt_suffix:
        lora.negative_prompt_suffix = metadata['negative_prompt_suffix']
        updated_fields.append('negative prompt')

    # Update guidance scale
    if metadata.get('guidance_scale') != lora.guidance_scale:
        lora.guidance_scale = metadata['guidance_scale']
        updated_fields.append('guidance scale')

    # Always update notes (contains stats)
    if 'notes' in metadata:
        lora.notes = metadata['notes']
        updated_fields.append('notes/stats')

    return updated_fields
```

**Step 3**: Simplified bulk action (15 min)
```python
@action(description=_("Refresh metadata from CivitAI"))
def refresh_metadata_bulk_action(self, request, queryset):
    """Refresh metadata from CivitAI for selected LoRAs."""
    loras_with_air = queryset.exclude(air='')

    if not loras_with_air.exists():
        self.message_user(
            request,
            "None of the selected LoRAs have CivitAI AIRs configured.",
            level=messages.WARNING
        )
        return

    # Process all LoRAs
    results = [
        _refresh_single_lora_metadata(lora, settings.CIVITAI_API_KEY)
        for lora in loras_with_air
    ]

    # Display results
    _display_bulk_refresh_results(self, request, results)
```

**Expected Outcome**:
- Complexity: 20 → 5 (main action)
- Helper functions: 3-5 complexity each
- Better error isolation (failures don't break the loop logic)

---

### 2.3 Refactor: `main()` in prompt_enhancer.py (Complexity: 17 → <10)

**File**: `lib/prompt_enhancer.py:605-779`
**Estimated Time**: 45 minutes

#### Refactoring Strategy

**Step 1**: Extract argument parsing (10 min)
```python
def _create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Enhance image generation prompts for diffusion models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_get_usage_examples()
    )

    _add_input_arguments(parser)
    _add_enhancement_arguments(parser)
    _add_llm_arguments(parser)
    _add_output_arguments(parser)

    return parser
```

**Step 2**: Extract enhancer factory (10 min)
```python
def _create_enhancer(args: argparse.Namespace) -> PromptEnhancer:
    """
    Factory for creating the appropriate enhancer.

    Args:
        args: Parsed command-line arguments

    Returns:
        Configured PromptEnhancer instance
    """
    if args.use_hf:
        return HFPromptEnhancer(
            model_id=args.hf_model,
            style=args.style,
            creativity=args.creativity,
            trigger_words=args.trigger_words
        )

    if args.use_llm:
        api_key = args.api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "--api-key required or set ANTHROPIC_API_KEY environment variable"
            )
        return LLMPromptEnhancer(
            api_key=api_key,
            model=args.model,
            style=args.style,
            creativity=args.creativity,
            trigger_words=args.trigger_words
        )

    return PromptEnhancer(
        style=args.style,
        creativity=args.creativity,
        trigger_words=args.trigger_words
    )
```

**Step 3**: Simplified main (15 min)
```python
def main():
    """CLI entry point for prompt enhancement."""
    parser = _create_argument_parser()
    args = parser.parse_args()

    # Handle special commands
    if args.list_hf_models:
        _display_available_models()
        return

    # Validate arguments
    _validate_arguments(args)

    # Create enhancer
    try:
        enhancer = _create_enhancer(args)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Process prompts
    results = _process_prompts(enhancer, args)

    # Output results
    _output_results(results, args)
```

**Expected Outcome**:
- Complexity: 17 → 4 (main function)
- Helper functions: 3-5 complexity each
- CLI logic separated from business logic

---

## Phase 3: Documentation & Metrics (30 minutes)

### 3.1 Document Remaining Issues
- **Action**: Create `docs/code-quality-remaining.md`
- **Contents**:
  - Moderate complexity functions (10-13)
  - Type hint coverage gaps
  - Missing tests
  - Performance optimization opportunities
- **Time**: 15 minutes

### 3.2 Final Metrics
- **Action**: Run all quality checks and save to `docs/code-quality-after.md`
- **Metrics to capture**:
  ```bash
  # Complexity
  uv run flake8 --max-complexity=10 --statistics

  # Line length
  uv run flake8 --select=E501 | wc -l

  # Import issues
  uv run flake8 --select=F401,E402 | wc -l
  ```
- **Time**: 15 minutes

---

## Testing Strategy

After each refactoring:

1. **Manual Smoke Test**
   - Run `uv run manage.py check`
   - Import affected modules in Django shell
   - Verify no syntax errors

2. **Functional Test** (if applicable)
   - Create test job via admin
   - Queue task
   - Verify completion

3. **Comparison Test**
   - Before/after flake8 complexity output
   - Verify complexity reduced as expected

---

## Rollback Plan

Each refactoring is in a separate commit:

```bash
# If issues found, revert specific commit
git revert <commit-hash>

# Or reset to before refactoring
git reset --hard HEAD~1
```

---

## Success Criteria

### Phase 1 (Quick Wins)
- ✅ All files formatted with Black
- ✅ Imports organized with isort
- ✅ Zero F401 (unused import) violations
- ✅ Zero E501 (line length) violations >100 chars

### Phase 2 (Critical Refactoring)
- ✅ `generate_images_task` complexity: 20 → <10
- ✅ `refresh_metadata_bulk_action` complexity: 20 → <10
- ✅ `main()` complexity: 17 → <10
- ✅ All functions passing complexity threshold
- ✅ No functionality broken (manual testing confirms)

### Phase 3 (Documentation)
- ✅ Before/after metrics documented
- ✅ Remaining issues cataloged with priorities
- ✅ Improvement plan for next iteration created

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking existing functionality | Low | High | Thorough manual testing after each change |
| Git conflicts with other work | Medium | Low | Frequent commits, clear commit messages |
| Introducing bugs during refactor | Low | Medium | Small, focused changes; test after each |
| Time overrun | Medium | Low | Can pause after any phase |

---

## Questions Before Starting?

1. **Timing**: Is now a good time, or should we wait for a quieter period?
2. **Scope**: Do all 3 critical functions need fixing now, or should we start with just 1?
3. **Testing**: Should I create basic unit tests for refactored functions?
4. **Branch**: Should this be done in a feature branch or directly on main?

---

## Next Steps After This Plan

Once approved, I will:

1. Create feature branch: `refactor/code-quality-improvements`
2. Execute Phase 1 (Quick Wins) - single commit
3. Execute Phase 2 refactorings - one commit per function
4. Execute Phase 3 documentation - final commit
5. Create summary report of improvements

**Ready to proceed?** Please review this plan and let me know if you'd like any adjustments.
