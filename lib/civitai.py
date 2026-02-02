"""
CivitAI integration for downloading LoRA files via AIR URN.

AIR format: urn:air:{ecosystem}:{type}:civitai:{modelId}@{versionId}
Download endpoint: GET https://civitai.com/api/download/models/{versionId}
"""
import re
from pathlib import Path

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
