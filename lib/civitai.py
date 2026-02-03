"""
CivitAI integration for downloading LoRA files via AIR URN.

AIR format: urn:air:{ecosystem}:{type}:civitai:{modelId}@{versionId}
Download endpoint: GET https://civitai.com/api/download/models/{versionId}
Metadata endpoint: GET https://civitai.com/api/v1/model-versions/{versionId}
"""
import re
from pathlib import Path
from typing import Optional

import requests


def parse_air(air_urn: str) -> tuple[str, str]:
    """
    Extract model ID and version ID from a CivitAI AIR URN.

    Args:
        air_urn: e.g. "urn:air:zimageturbo:lora:civitai:2344335@2636956"

    Returns:
        (model_id, version_id) as strings

    Raises:
        ValueError: If the AIR URN cannot be parsed
    """
    match = re.search(r'civitai:(\d+)@(\d+)', air_urn)
    if not match:
        raise ValueError(f"Cannot parse CivitAI AIR URN: {air_urn}")
    return match.group(1), match.group(2)


def fetch_model_version_metadata(version_id: str, api_key: Optional[str] = None) -> dict:
    """
    Fetch metadata for a model version from CivitAI API.

    Args:
        version_id: CivitAI model version ID
        api_key: Optional CivitAI API key for authentication

    Returns:
        Dictionary containing model version metadata

    Raises:
        RuntimeError: If API request fails
    """
    url = f"https://civitai.com/api/v1/model-versions/{version_id}"
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    print(f"DEBUG: Fetching metadata from CivitAI (version={version_id})")

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json()
    print(f"DEBUG: Fetched metadata for '{data.get('name', 'Unknown')}'")

    return data


def extract_lora_metadata(metadata: dict) -> dict:
    """
    Extract relevant LoRA fields from CivitAI model version metadata.

    Args:
        metadata: Raw metadata from CivitAI API

    Returns:
        Dictionary with extracted fields suitable for LoraModel creation
    """
    # Map CivitAI baseModel to our base_architecture choices
    base_model_map = {
        'SD 1.5': 'sd15',
        'SD 2.1': 'sd15',  # Close enough
        'SDXL 1.0': 'sdxl',
        'SDXL 0.9': 'sdxl',
        'SDXL Turbo': 'sdxl',
        'Pony': 'sdxl',  # Pony is SDXL-based
        'Flux.1 D': 'flux1',
        'Flux.1 S': 'flux1',
    }

    # Extract base architecture
    base_model = metadata.get('baseModel', '')
    base_architecture = base_model_map.get(base_model, 'sdxl')  # Default to SDXL

    # Extract trigger words
    trained_words = metadata.get('trainedWords', [])
    prompt_suffix = ', '.join(trained_words) if trained_words else ''

    # Try to get guidance scale from example images
    guidance_scale = None
    images = metadata.get('images', [])
    if images and images[0]:
        # Look at the first image's meta for cfgScale
        first_image_meta = images[0].get('meta') or {}
        cfg = first_image_meta.get('cfgScale')
        if cfg:
            guidance_scale = float(cfg)

    # Extract negative prompt examples
    negative_prompt_suffix = ''
    if images and images[0]:
        first_image_meta = images[0].get('meta') or {}
        neg_prompt = first_image_meta.get('negativePrompt', '')
        if neg_prompt:
            negative_prompt_suffix = neg_prompt

    # Build extracted metadata
    extracted = {
        'label': metadata.get('name', ''),
        'base_architecture': base_architecture,
        'prompt_suffix': prompt_suffix,
        'negative_prompt_suffix': negative_prompt_suffix,
        'notes': metadata.get('description', ''),
    }

    # Add guidance_scale only if we found it
    if guidance_scale:
        extracted['guidance_scale'] = guidance_scale

    # Add stats for reference
    stats = metadata.get('stats', {})
    if stats:
        stats_text = f"\n\nCivitAI Stats: {stats.get('downloadCount', 0):,} downloads, {stats.get('rating', 0):.1f}★ ({stats.get('ratingCount', 0)} ratings)"
        extracted['notes'] = (extracted['notes'] or '') + stats_text

    return extracted


def download_lora(air_urn: str, dest_path: str, api_key: str) -> str:
    """
    Download a LoRA file from CivitAI using its AIR URN.

    Args:
        air_urn: CivitAI AIR URN containing model/version IDs
        dest_path: Local path where the file should be saved
        api_key: CivitAI API key for authentication

    Returns:
        The dest_path string on success

    Raises:
        ValueError: If AIR cannot be parsed
        RuntimeError: If download fails
    """
    if not api_key:
        raise RuntimeError("CIVITAI_API_KEY is not configured")

    model_id, version_id = parse_air(air_urn)

    url = f"https://civitai.com/api/download/models/{version_id}"
    headers = {"Authorization": f"Bearer {api_key}"}

    print(f"DEBUG: Downloading LoRA from CivitAI (model={model_id}, version={version_id})")

    response = requests.get(url, headers=headers, stream=True, timeout=300)
    response.raise_for_status()

    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Stream to a temp file then rename for atomicity
    tmp_path = dest.with_suffix('.tmp')
    size = 0
    try:
        with open(tmp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                size += len(chunk)
        tmp_path.rename(dest)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    print(f"DEBUG: Downloaded LoRA to {dest_path} ({size / 1024 / 1024:.1f} MB)")
    return dest_path
