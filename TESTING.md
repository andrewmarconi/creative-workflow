# Testing Guide - QueerChaos 2

## Phase 5: Testing Checklist

This document outlines the testing plan for the QueerChaos 2 image generation system.

## Pre-Test Setup

### 1. Environment Verification

```bash
# Verify uv environment is active
python --version  # Should be 3.12+

# Verify all dependencies installed
python -c "import torch, diffusers, transformers; print('✓ Dependencies OK')"

# Verify MPS (Apple Silicon) is available
python -c "import torch; print(f'MPS Available: {torch.backends.mps.is_available()}')"
```

### 2. HuggingFace Authentication

```bash
# Login to HuggingFace (required for model downloads)
huggingface-cli login

# Verify authentication
huggingface-cli whoami
```

## Test Scenarios

### ✅ Test 1: Single Prompt (Basic Functionality)

**Purpose**: Verify basic image generation works

**Test File**: `tests/test_single_prompt.json`

**Expected Behavior**:
- Loads models successfully
- Generates 1 image
- Creates output directory
- Saves metadata JSON
- Exit code 0

**Command**:
```bash
python generate.py tests/test_single_prompt.json
```

**Validation**:
```bash
ls outputs/test_single/
# Expected files:
# - sunset_001.jpg
# - generation_metadata.json
# - .checkpoint.json
```

---

### ✅ Test 2: Multiple Prompts

**Purpose**: Verify batch processing with multiple prompts

**Test File**: `tests/test_multiple_prompts.json`

**Expected Behavior**:
- Generates 6 images (3 prompts × 2 count)
- Progress bar shows correct totals
- All images saved with correct naming
- Exit code 0

**Command**:
```bash
python generate.py tests/test_multiple_prompts.json
```

**Validation**:
```bash
ls outputs/test_multiple/ | wc -l
# Expected: 9 files (6 images + metadata + checkpoint + directory)

# Verify naming convention
ls outputs/test_multiple/*.jpg
# Expected:
# - cityscape_001.jpg, cityscape_002.jpg
# - nature_001.jpg, nature_002.jpg
# - portrait_001.jpg, portrait_002.jpg
```

---

### ✅ Test 3: With HuggingFace LoRA

**Purpose**: Verify LoRA loading from HuggingFace Hub

**Test File**: `tests/test_with_lora_hf.json`

**Expected Behavior**:
- Downloads LoRA from HuggingFace
- Appends LoRA prompt to each prompt
- Generates 4 images
- Metadata includes LoRA info

**Command**:
```bash
python generate.py tests/test_with_lora_hf.json
```

**Validation**:
```bash
# Check metadata includes LoRA
cat outputs/test_lora_hf/generation_metadata.json | grep "lora"

# Verify prompts include LoRA text
cat outputs/test_lora_hf/generation_metadata.json | grep "in 80s cyberpunk style"
```

**Note**: This test requires the LoRA model to exist on HuggingFace Hub. If the model doesn't exist, expect a failure.

---

### ✅ Test 4: With Local LoRA

**Purpose**: Verify LoRA loading from local .safetensors file

**Test File**: `tests/test_with_lora_local.json`

**Prerequisites**:
```bash
# Create mock models directory (or use real LoRA file)
mkdir -p models
# Place a valid .safetensors LoRA file at:
# models/custom_style.safetensors
```

**Expected Behavior**:
- Loads LoRA from local file
- If file doesn't exist, fails with clear error
- If file exists, generates images with LoRA applied

**Command**:
```bash
python generate.py tests/test_with_lora_local.json
```

**Expected Error (if file missing)**:
```
✗ Failed to load LoRA './models/custom_style.safetensors': [Errno 2] No such file or directory
```

---

### ✅ Test 5: Resume Functionality

**Purpose**: Verify checkpoint/resume system works

**Test File**: `tests/test_resume.json`

**Test Steps**:

1. **Start generation and interrupt**:
   ```bash
   python generate.py tests/test_resume.json
   # Wait for 2-3 images to complete, then press Ctrl+C
   ```

2. **Verify checkpoint exists**:
   ```bash
   cat outputs/test_resume/.checkpoint.json
   # Should show completed_images list
   ```

3. **Resume from checkpoint**:
   ```bash
   python generate.py tests/test_resume.json
   # Should show: "✓ Loaded checkpoint: N images already completed"
   # Should skip completed images and continue from where it left off
   ```

4. **Verify no duplicates**:
   ```bash
   ls outputs/test_resume/*.jpg | wc -l
   # Should be exactly 15 images (3 prompts × 5 count)
   ```

**Expected Behavior**:
- First run: Generates some images before interruption
- Checkpoint saved after each image
- Second run: Loads checkpoint, skips completed, continues
- Progress bar shows Skipped count
- Final result: All 15 images generated (no duplicates)

---

### ✅ Test 6: Error Handling - Invalid JSON

**Purpose**: Verify JSON parsing error handling

**Test File**: `tests/test_invalid_json.json`

**Expected Behavior**:
- Detects malformed JSON
- Exits with code 1
- Shows clear error message

**Command**:
```bash
python generate.py tests/test_invalid_json.json
echo "Exit code: $?"
```

**Expected Output**:
```
✗ JSON Parse Error: ...
Exit code: 1
```

---

### ✅ Test 7: Error Handling - Missing Required Fields

**Purpose**: Verify schema validation

**Test File**: `tests/test_missing_fields.json`

**Expected Behavior**:
- Detects missing `output_dir` field
- Exits with code 1
- Shows validation error

**Command**:
```bash
python generate.py tests/test_missing_fields.json
echo "Exit code: $?"
```

**Expected Output**:
```
✗ Validation Error: Missing required fields: output_dir
Exit code: 1
```

---

### ✅ Test 8: CLI Interface

**Purpose**: Verify command-line argument handling

**Tests**:

1. **Help display**:
   ```bash
   python generate.py --help
   ```
   Expected: Shows usage information

2. **Default input file**:
   ```bash
   python generate.py
   ```
   Expected: Uses `./input.json` (will fail if doesn't exist)

3. **Custom input file**:
   ```bash
   python generate.py tests/test_single_prompt.json
   ```
   Expected: Uses specified file

4. **Non-existent file**:
   ```bash
   python generate.py nonexistent.json
   echo "Exit code: $?"
   ```
   Expected: Error message, exit code 1

---

## Memory Usage Testing (M4 Mac Specific)

### Test 9: Memory Monitoring

**Purpose**: Verify memory usage stays within 48GB RAM limits

**Setup**:
```bash
# In a separate terminal, monitor memory usage
watch -n 1 "ps aux | grep python | grep generate"

# Or use Activity Monitor to watch Python process
```

**Test**:
```bash
python generate.py tests/test_multiple_prompts.json
```

**Observations to Record**:
- Peak memory usage during model loading
- Memory usage during generation
- Memory freed after MPS cache clear
- Any OOM errors

**Expected Behavior**:
- Memory usage stays reasonable (<30GB)
- MPS cache clearing prevents memory accumulation
- No crashes or OOM errors

---

## Automated Validation Tests

### Quick Validation Suite

Run all quick validation tests:

```bash
# Test 1: Syntax check
python -m py_compile generate.py && echo "✓ Syntax OK"

# Test 2: Import check
python -c "from generate import *; print('✓ Imports OK')"

# Test 3: JSON validation
python -c "
from generate import load_input_json
load_input_json('tests/test_single_prompt.json')
print('✓ JSON validation OK')
"

# Test 4: CLI help
python generate.py --help > /dev/null && echo "✓ CLI OK"
```

---

## Test Results Documentation

### Test Result Template

For each test, document:

```markdown
## Test: [Test Name]
**Date**: YYYY-MM-DD
**Environment**: M4 Mac, 48GB RAM, macOS version
**Status**: ✅ PASS / ✗ FAIL

**Results**:
- Images generated: X/Y
- Generation time: Xm Ys per image
- Memory usage: Peak XGB
- Exit code: X

**Issues** (if any):
- Description of any problems
- Error messages
- Unexpected behavior

**Notes**:
- Any observations
- Performance metrics
```

---

## Known Limitations

1. **Model Availability**: Tests require Flux2 Dev and text encoder to be available on HuggingFace
2. **Authentication**: HuggingFace login required
3. **Download Time**: First run downloads ~15GB of models
4. **Generation Time**: Each image takes 30-60 seconds on M4 Mac
5. **LoRA Tests**: Require valid LoRA models (HuggingFace or local)

---

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'diffusers'`
**Solution**: Run `uv sync` to install dependencies

**Issue**: `MPS not available`
**Solution**: Verify running on Apple Silicon Mac with macOS 12.3+

**Issue**: `Failed to load model`
**Solution**:
- Check HuggingFace authentication: `huggingface-cli whoami`
- Verify internet connection
- Check model ID is correct

**Issue**: `Out of memory`
**Solution**:
- Reduce batch size (count)
- Ensure no other memory-intensive apps running
- Check MPS cache is being cleared

---

## Success Criteria

Phase 5 testing is complete when:

- ✅ All 8 test scenarios pass
- ✅ No syntax or import errors
- ✅ JSON validation works correctly
- ✅ Resume functionality verified
- ✅ Error handling works as expected
- ✅ Memory usage is reasonable
- ✅ Generated images are valid JPG files
- ✅ Metadata is accurate and complete
- ✅ Exit codes are correct

---

## Next Steps After Testing

Once all tests pass:

1. Update README with tested version info
2. Tag release: `v0.1.0`
3. Document any discovered issues
4. Create GitHub issues for future enhancements
5. Consider additional features (see prd.md for ideas)
