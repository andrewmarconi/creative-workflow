# Logging Requirements for Adaptations Feature

## Overview

All code, especially long-running Celery tasks, must produce structured JSON logs compatible with the Grafana/Loki stack. Logs must be verbose enough to track progress, debug issues, and measure performance.

## Logging Standards

### Use Structured Logging

All logs must use the existing `structlog` configuration. Import and use the logger consistently:

```python
import structlog

logger = structlog.get_logger(__name__)
```

### Log Levels

| Level | Use Case |
|-------|----------|
| `DEBUG` | Detailed diagnostic info (disabled in production) |
| `INFO` | Normal operation milestones, progress updates |
| `WARNING` | Unexpected but recoverable situations |
| `ERROR` | Failures that need attention |

### Required Context Fields

Every log entry should include relevant context:

```python
logger.info(
    "adaptation_started",
    tv_spot_id=tv_spot.id,
    tv_spot_title=tv_spot.script_title,
    market_id=market.id,
    market_code=market.code,
    task_id=self.request.id,  # Celery task ID
)
```

## Task Logging Patterns

### Task Lifecycle

Every Celery task must log:

1. **Start**: When task begins
2. **Progress**: At meaningful milestones
3. **Completion**: When task succeeds
4. **Failure**: When task fails (with error details)

```python
@shared_task(bind=True)
def create_adaptation_task(self, tv_spot_id: int, market_id: int):
    logger.info(
        "create_adaptation_started",
        task_id=self.request.id,
        tv_spot_id=tv_spot_id,
        market_id=market_id,
    )

    try:
        tv_spot = TvSpot.objects.get(id=tv_spot_id)
        market = AdaptationMarket.objects.get(id=market_id)

        logger.info(
            "adaptation_context_loaded",
            task_id=self.request.id,
            tv_spot_title=tv_spot.script_title,
            market_name=market.name,
            origin_row_count=tv_spot.origin_version.script_rows.count(),
        )

        # ... adaptation logic ...

        logger.info(
            "llm_generation_started",
            task_id=self.request.id,
            prompt_length=len(prompt),
            model="qwen3-8b",
        )

        adapted_json = generate_with_outlines(prompt, schema)

        logger.info(
            "llm_generation_completed",
            task_id=self.request.id,
            output_length=len(json.dumps(adapted_json)),
            row_count=len(adapted_json.get('script_rows', [])),
        )

        version = create_version_from_json(tv_spot, market, adapted_json)

        logger.info(
            "create_adaptation_completed",
            task_id=self.request.id,
            tv_spot_id=tv_spot_id,
            market_id=market_id,
            version_id=version.id,
            version_code=version.code,
        )

        return version.id

    except Exception as e:
        logger.error(
            "create_adaptation_failed",
            task_id=self.request.id,
            tv_spot_id=tv_spot_id,
            market_id=market_id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise
```

### Storyboard Generation Logging

For `generate_storyboard_task`, log each step:

```python
@shared_task(bind=True)
def generate_storyboard_task(self, storyboard_job_id: int):
    logger.info(
        "storyboard_generation_started",
        task_id=self.request.id,
        storyboard_job_id=storyboard_job_id,
    )

    job = StoryboardJob.objects.get(id=storyboard_job_id)
    version = job.tv_spot_version
    rows = version.script_rows.all()

    logger.info(
        "storyboard_context_loaded",
        task_id=self.request.id,
        storyboard_job_id=storyboard_job_id,
        version_code=version.code,
        row_count=rows.count(),
        images_per_row=job.images_per_row,
        total_images=rows.count() * job.images_per_row,
        model_name=job.diffusion_model.label,
        lora_name=job.lora_model.label if job.lora_model else None,
    )

    for idx, row in enumerate(rows):
        logger.info(
            "generating_prompt_for_row",
            task_id=self.request.id,
            storyboard_job_id=storyboard_job_id,
            row_index=idx,
            row_count=rows.count(),
            shot_number=row.shot_number,
        )

        prompt = generate_image_prompt(version, row, job.diffusion_model)

        logger.info(
            "prompt_generated",
            task_id=self.request.id,
            row_index=idx,
            prompt_length=len(prompt),
        )

        # Create DiffusionJobs for this row
        for img_idx in range(job.images_per_row):
            diffusion_job = create_diffusion_job(...)

            logger.info(
                "diffusion_job_created",
                task_id=self.request.id,
                storyboard_job_id=storyboard_job_id,
                diffusion_job_id=diffusion_job.id,
                row_index=idx,
                image_index=img_idx,
                identifier=diffusion_job.identifier,
            )

    logger.info(
        "storyboard_generation_completed",
        task_id=self.request.id,
        storyboard_job_id=storyboard_job_id,
        jobs_created=rows.count() * job.images_per_row,
    )
```

## Loki Query Examples

### Find all adaptation tasks for a TV spot

```logql
{job="celery"} | json | tv_spot_id="123"
```

### Find failed tasks

```logql
{job="celery"} | json | level="ERROR" | line_format "{{.error}}"
```

### Track storyboard progress

```logql
{job="celery"} | json | storyboard_job_id="456" | line_format "{{.msg}}: row {{.row_index}}/{{.row_count}}"
```

### Measure LLM generation time

```logql
{job="celery"} | json | msg=~"llm_generation.*" | line_format "{{.task_id}}: {{.msg}}"
```

## Performance Metrics

Log timing for slow operations:

```python
import time

start = time.perf_counter()
result = expensive_operation()
elapsed = time.perf_counter() - start

logger.info(
    "operation_completed",
    operation="llm_generation",
    duration_seconds=round(elapsed, 3),
    task_id=self.request.id,
)
```

## Checklist for New Code

- [ ] All tasks log start, progress, completion, and failure
- [ ] Context fields include relevant IDs (task_id, job_id, version_id, etc.)
- [ ] Errors include `error_type`, `error` message, and `exc_info=True`
- [ ] Progress logs include current/total counts for iterations
- [ ] Timing is logged for LLM calls and other slow operations
- [ ] Log messages use snake_case event names (e.g., `adaptation_started`, not "Adaptation started")
