# Video Upload Security Implementation Summary

## Overview

Comprehensive security validation system has been implemented for video file uploads in the tvspots app. This provides multiple layers of protection against malicious uploads, DoS attacks, and file-based exploits.

## Implementation Details

### New Files Created

1. **`src/cw/lib/security/__init__.py`** - Security module exports
2. **`src/cw/lib/security/file_validation.py`** - All validator classes (585 lines)
3. **`src/cw/tvspots/tests/test_security_validation.py`** - Comprehensive test suite (638 lines, 44 tests)
4. **`docs/security/video-upload-security.md`** - Complete documentation

### Modified Files

1. **`src/cw/settings.py`**
   - Added 15 security configuration settings
   - Added security logging configuration

2. **`src/cw/tvspots/models.py`**
   - Modified `AdUnitMedia.save()` to validate uploads

3. **`src/cw/tvspots/admin.py`**
   - Refactored `bulk_upload_videos_view()` to use security validators

## Security Features Implemented

### 1. File Size Validation (`FileSizeValidator`)
- Enforces configurable max size (default: 500 MB)
- Prevents empty file uploads (min: 1 byte)
- Settings: `VIDEO_MAX_UPLOAD_SIZE_BYTES`

### 2. Extension Validation (`FileExtensionValidator`)
- Whitelist-only approach
- Case-insensitive matching
- Prevents executables and dangerous formats
- Settings: `VIDEO_ALLOWED_EXTENSIONS`

### 3. MIME Type Validation (`MimeTypeValidator`)
- Uses libmagic for content-based detection
- Prevents extension-based spoofing
- Logs MIME mismatches
- Settings: `VIDEO_ALLOWED_MIME_TYPES`, `VIDEO_VERIFY_MIME_CONTENT`

### 4. File Header Validation (`FileHeaderValidator`)
- Validates magic bytes against known signatures
- Supports MP4, MOV, AVI, MKV, WebM
- Independent verification layer
- Settings: `VIDEO_VALIDATE_HEADERS`

### 5. Filename Sanitization (`FilenameSanitizer`)
- Removes path traversal attempts (`../../../`)
- Handles Windows paths (`C:\Windows\...`)
- Removes dangerous characters (`<>:|?*`)
- Removes control characters (`\x00-\x1f`)
- Replaces spaces with underscores (optional)
- Truncates long filenames (max 255 chars)
- Settings: `VIDEO_SANITIZE_FILENAMES`

### 6. Composite Validator (`VideoFileValidator`)
- Chains all validators together
- Single entry point for validation
- Bulk validation support via `validate_multiple()`
- Configurable validator enable/disable

## Security Audit Logging

All validation events are logged to `logs/tasks.log` in JSON format:

**Log Events:**
- `file_upload_validation_started` - Validation begins
- `file_upload_validation_passed` - All checks passed
- `file_upload_validation_failed` - Validation failed
- `filename_sanitized` - Filename was modified
- `mime_type_mismatch` - Declared vs detected MIME mismatch

**Log Fields:**
- `event` - Event type
- `validator` - Validator class name
- `upload_filename` - Original filename
- `file_size` - File size in bytes
- `content_type` - Declared MIME type
- `reason` - Failure reason (if failed)
- Additional context fields per validator

## Configuration

All settings in `src/cw/settings.py`:

```python
# File Size Limits
VIDEO_MAX_UPLOAD_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB

# Allowed Extensions
VIDEO_ALLOWED_EXTENSIONS = [".mp4", ".mov", ".avi", ".mkv", ".webm"]

# Allowed MIME Types
VIDEO_ALLOWED_MIME_TYPES = [
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
    "video/webm",
]

# Validation Options
VIDEO_VERIFY_MIME_CONTENT = True  # Use libmagic
VIDEO_VALIDATE_HEADERS = True     # Check magic bytes
VIDEO_SANITIZE_FILENAMES = True   # Sanitize filenames

# Future: Rate Limiting (settings ready, implementation pending)
VIDEO_UPLOAD_RATE_LIMIT_ENABLED = False
VIDEO_UPLOAD_RATE_LIMIT_PER_USER = 10
VIDEO_UPLOAD_RATE_LIMIT_PER_IP = 20

# Future: Virus Scanning (settings ready, implementation pending)
VIDEO_VIRUS_SCAN_ENABLED = False
VIDEO_VIRUS_SCAN_ENDPOINT = ""
```

## Testing

Comprehensive test suite with 44 tests covering all validators:

```bash
# Run all security tests
uv run pytest src/cw/tvspots/tests/test_security_validation.py -v

# Test results: 44 passed, 0 failed
```

**Test Coverage:**
- File size validation (6 tests)
- Extension validation (6 tests)
- MIME type validation (6 tests)
- File header validation (6 tests)
- Filename sanitization (9 tests)
- Composite validator (8 tests)
- Security logging (3 tests)

## Usage Examples

### In Models (Automatic)
```python
# AdUnitMedia.save() automatically validates uploads
media = AdUnitMedia.objects.create(
    campaign=campaign,
    video_file=uploaded_file,  # Validated automatically
)
```

### In Admin Views
```python
from cw.lib.security import VideoFileValidator

validator = VideoFileValidator()
video_files = request.FILES.getlist('video_files')

# Validate all files
results = validator.validate_multiple(video_files)

for filename, errors in results.items():
    if errors:
        messages.error(request, f"{filename}: {', '.join(errors)}")
```

### Custom Validation
```python
from cw.lib.security import VideoFileValidator

validator = VideoFileValidator(
    max_size_bytes=100 * 1024 * 1024,  # 100 MB
    verify_mime_content=True,
    validate_headers=True,
)

try:
    validator.validate(uploaded_file)
except ValidationError as e:
    # Handle validation failure
    pass
```

## Threat Mitigation

### Mitigated Threats ✅
- **File Type Spoofing** - MIME verification + header validation
- **Path Traversal** - Filename sanitization
- **Malicious Executables** - Extension whitelisting + header validation
- **Denial of Service** - File size limits
- **Storage Exhaustion** - File size limits
- **Command Injection** - Filename sanitization
- **Malformed Filenames** - Sanitization + validation

### Future Enhancements 🔲
- **Rate Limiting** - Prevent upload abuse
- **Virus Scanning** - ClamAV integration
- **Content Analysis** - Codec validation with ffmpeg
- **Duplicate Detection** - Hash-based deduplication
- **Automated Cleanup** - Remove failed uploads
- **IP Blocking** - Block repeat offenders

## Dependencies

- **python-magic** (>=0.4.27) - MIME type detection via libmagic
- **libmagic** (system library) - File type identification
- Django 6.0+ - ValidationError, file upload handling

## Installation Notes

**System Requirements:**
```bash
# macOS
brew install libmagic

# Ubuntu/Debian
sudo apt-get install libmagic1

# Then sync Python dependencies
uv sync
```

## Documentation

Comprehensive documentation available at:
- **`docs/security/video-upload-security.md`** - Full security guide
  - Architecture overview
  - Validator class reference
  - Usage examples
  - Configuration guide
  - Troubleshooting
  - Security best practices

## Integration Points

1. **Model Save Hook** - `AdUnitMedia.save()` validates on creation
2. **Bulk Upload View** - `CampaignAdmin.bulk_upload_videos_view()` validates all files
3. **Admin Inline** - `AdUnitMediaInline` saves trigger validation
4. **Future**: Django Forms, REST API endpoints

## Security Best Practices

1. ✅ Never trust file extensions - Content-based validation implemented
2. ✅ Validate on upload - Checks before saving to disk
3. ✅ Sanitize filenames - Path traversal prevention
4. ✅ Log all events - Complete audit trail
5. ✅ Multiple layers - Don't rely on single check
6. ⚠️ Monitor logs - Set up Grafana alerts (manual)
7. ⚠️ Review limits - Periodic review needed

## Performance Impact

- **File Size Check**: O(1) - Instant
- **Extension Check**: O(1) - String comparison
- **MIME Detection**: O(1) - Reads first 8KB only
- **Header Check**: O(1) - Reads first 32 bytes only
- **Filename Sanitization**: O(n) - Linear in filename length

**Overall**: Minimal performance impact (<10ms per file for typical videos)

## Maintenance

### Adding New Video Formats
1. Update `VIDEO_ALLOWED_EXTENSIONS` in settings
2. Update `VIDEO_ALLOWED_MIME_TYPES` in settings
3. Add signature to `FileHeaderValidator.VIDEO_SIGNATURES`
4. Add test case to test suite

### Adjusting Limits
1. Update `VIDEO_MAX_UPLOAD_SIZE_BYTES` in settings
2. Consider disk space and bandwidth constraints
3. Test with production-scale files

## Notes

- All validators can be individually disabled via `enabled=False`
- Validators run in sequence (short-circuit on first failure)
- Filename sanitization modifies `file.name` in-place
- All validation failures are logged for security auditing
- Compatible with Django's file upload handling
