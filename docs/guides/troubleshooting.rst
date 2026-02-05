Troubleshooting
===============

Common issues and solutions when working with Generative Creative Lab.

Model Loading Issues
--------------------

**Models fail to download or load?**

1. **Verify HuggingFace authentication** for community models::

    huggingface-cli login

2. **Check MODEL_BASE_PATH** in ``.env`` for local model files - ensure the
   path exists and contains the expected ``.safetensors`` files.

3. **Ensure model architecture matches** available implementations - check that
   the ``pipeline`` field in ``presets.json`` corresponds to a registered model
   class in ``cw.lib.models``.

4. **Check available disk space** - models require 2-15GB each depending on
   architecture. The HuggingFace cache is typically at ``~/.cache/huggingface/``.

**Model loads but generation fails?**

- Check GPU memory availability - only one model loads at a time by design
- Review Celery worker logs at ``logs/worker_default.log`` for error details
- Try a smaller model (Z-Image Turbo, SDXL Turbo) to verify basic functionality

LoRA and Style Issues
---------------------

**LoRA not applying or style looks wrong?**

1. **Verify base_architecture matches** - LoRAs only work with compatible models.
   An SDXL LoRA won't work with Flux models::

    # In presets.json, ensure LoRA matches model architecture
    "base_architecture": "sdxl"  # Must match target model

2. **Check CivitAI AIR URN validity** - if using auto-download, ensure the AIR
   URN format is correct::

    "air": "urn:air:sdxl:lora:civitai:123456@789012"

3. **Confirm LoRA strength settings** - values should be between 0.0 and 1.0.
   Start with 0.7-0.8 for most LoRAs::

    "settings": {"strength": 0.8}

4. **Check trigger words** - ensure the ``prompt_suffix`` contains required
   trigger words for the LoRA to activate.

**CivitAI download fails?**

- Verify ``CIVITAI_API_KEY`` is set in ``.env``
- Check the AIR URN format matches CivitAI's model version ID
- Some models may be restricted or require acceptance of terms on CivitAI

Performance Issues
------------------

**Generation is slow?**

- **Use turbo models for iteration** - Z-Image Turbo and SDXL Turbo generate
  in 4-9 steps vs 28-50 for quality models
- **Only one model loads at a time** - this is intentional to manage GPU memory
- **MPS/CUDA cache clears automatically** after each generation to prevent
  memory buildup

**Out of memory errors?**

- Reduce image dimensions (start with 512x512 or 768x768)
- Close other GPU-intensive applications
- For CUDA: consider enabling ``use_sequential_cpu_offload`` in model settings
- Restart the Celery worker to clear accumulated memory

Prompt Enhancement Issues
-------------------------

**LLM enhancement not working?**

1. **Check the enhancement worker** is running::

    uv run honcho start  # Starts all workers including enhancement

2. **Verify model downloads** - the Qwen2.5-3B model downloads on first use
   (~6GB)

3. **Check enhancement queue** - prompts are processed asynchronously on the
   ``enhancement`` queue

**API enhancement fails?**

- Verify ``ANTHROPIC_API_KEY`` is set in ``.env``
- Check API rate limits and account status
- Review logs at ``logs/worker_enhancement.log``

Database and Migration Issues
-----------------------------

**Database connection errors?**

1. **Ensure Docker containers are running**::

    docker compose up -d  # Start PostgreSQL and Valkey

2. **Check connection settings** in ``.env``::

    POSTGRES_HOST=localhost
    POSTGRES_PORT=5435
    POSTGRES_DB=cw
    POSTGRES_USER=cw
    POSTGRES_PASSWORD=cw

**Migration errors after updates?**

For development environments, migrations can be reset::

    # WARNING: This deletes all data
    uv run manage.py migrate --fake diffusion zero
    uv run manage.py migrate --fake tvspots zero
    uv run manage.py migrate
    uv run manage.py import_presets

Admin Interface Issues
----------------------

**Can't access admin at localhost:8000?**

1. **Verify Django is running**::

    uv run manage.py runserver  # Should show "Starting development server"

2. **Create a superuser** if you haven't::

    uv run manage.py createsuperuser

3. **Check for port conflicts** - ensure nothing else is using port 8000

**Images not displaying in admin?**

- Verify ``media/`` directory exists and is writable
- Check that ``MEDIA_URL`` and ``MEDIA_ROOT`` are configured in settings
- Generated images are saved to ``media/diffusion/``

Getting Help
------------

If you're still stuck:

1. Check the full logs at ``logs/*.log``
2. Review the :doc:`/architecture` for system understanding
3. Open an issue on GitHub with:
   - Error messages and stack traces
   - Steps to reproduce
   - System information (OS, GPU, Python version)
