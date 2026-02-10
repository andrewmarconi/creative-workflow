# Video Upload Security

This document describes the comprehensive security validation system for video file uploads in the tvspots app.

## Overview

The video upload security system provides multiple layers of protection against malicious file uploads, including:

1. **File Size Validation** - Prevents DoS attacks and ensures storage limits
2. **Extension Whitelisting** - Only allows specific video file extensions
3. **MIME Type Verification** - Validates actual file content, not just declared type
4. **File Header Validation** - Checks magic bytes to prevent file type spoofing
5. **Filename Sanitization** - Removes dangerous characters and path traversal attempts
6. **Security Audit Logging** - All validation events are logged for security monitoring

## Architecture

### Components

```
src/cw/lib/security/
├── __init__.py
└── file_validation.py        # All validator classes
```

### Validator Classes

#### `FileSecurityValidator` (Base Class)
Abstract base class for all validators. Provides:
- Logging framework for security auditing
- Enable/disable functionality
- Consistent validation interface

#### `FileSizeValidator`
Validates file size against configurable limits.

**Configuration:**
```python
# settings.py
VIDEO_MAX_UPLOAD_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB (default)
```

**Features:**
- Configurable max size (bytes)
- Configurable min size (default: 1 byte)
- Prevents empty file uploads
- Clear error messages with size in MB

**Example:**
```python
validator = FileSizeValidator(max_size_bytes=100 * 1024 * 1024)  # 100 MB
validator.validate(uploaded_file)
```

#### `FileExtensionValidator`
Validates file extension against a whitelist.

**Configuration:**
```python
# settings.py
VIDEO_ALLOWED_EXTENSIONS = [".mp4", ".mov", ".avi", ".mkv", ".webm"]
```

**Features:**
- Case-insensitive matching
- Prevents executable files (.exe, .bat, .sh, etc.)
- Prevents misleading double extensions

**Example:**
```python
validator = FileExtensionValidator(allowed_extensions={".mp4", ".mov"})
validator.validate(uploaded_file)
```

#### `MimeTypeValidator`
Validates MIME type using actual file content (libmagic).

**Configuration:**
```python
# settings.py
VIDEO_ALLOWED_MIME_TYPES = [
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
    "video/webm",
]
VIDEO_VERIFY_MIME_CONTENT = True  # Use libmagic for content detection
```

**Features:**
- Uses python-magic (libmagic) to detect actual file type
- Prevents extension-based spoofing (e.g., malware.exe renamed to malware.mp4)
- Logs warnings when declared and detected MIME types don't match
- Can be configured to skip content verification (faster but less secure)

**Example:**
```python
validator = MimeTypeValidator(
    allowed_mime_types={"video/mp4"},
    verify_content=True  # Inspect file content
)
validator.validate(uploaded_file)
```

#### `FileHeaderValidator`
Validates file headers (magic bytes) against known video signatures.

**Configuration:**
```python
# settings.py
VIDEO_VALIDATE_HEADERS = True
```

**Supported Signatures:**
- MP4: `\x00\x00\x00\x18ftypmp42` (and variants)
- MOV: `\x00\x00\x00\x14ftypqt  `
- AVI: `RIFF`
- MKV/WebM: `\x1A\x45\xDF\xA3` (EBML header)

**Features:**
- Checks first 32 bytes of file
- Detects file format independently of extension/MIME type
- Prevents spoofed files (e.g., executable with .mp4 extension)

**Example:**
```python
validator = FileHeaderValidator()
validator.validate(uploaded_file)
```

#### `FilenameSanitizer`
Sanitizes filenames to prevent path traversal and other attacks.

**Configuration:**
```python
# settings.py
VIDEO_SANITIZE_FILENAMES = True
```

**Features:**
- Removes path components (`../../../etc/passwd` → `passwd`)
- Removes dangerous characters (`<>:|?*`)
- Removes control characters (`\x00-\x1f`)
- Optionally replaces spaces with underscores
- Optionally converts to lowercase
- Truncates long filenames (max 255 chars)
- Replaces empty names with "unnamed"

**Example:**
```python
sanitizer = FilenameSanitizer(
    remove_path_components=True,
    replace_spaces=True,
    lowercase=False
)
sanitizer.validate(uploaded_file)
# uploaded_file.name is modified in-place
```

#### `VideoFileValidator` (Composite)
Chains all validators together for comprehensive validation.

**Features:**
- Single entry point for all video file validation
- Runs all enabled validators in sequence
- Collects all validation errors
- Provides `validate_multiple()` for bulk uploads

**Example:**
```python
from cw.lib.security import VideoFileValidator

# Use with all defaults from settings
validator = VideoFileValidator()
validator.validate(uploaded_file)

# Or customize
validator = VideoFileValidator(
    max_size_bytes=100 * 1024 * 1024,
    allowed_extensions={".mp4", ".mov"},
    verify_mime_content=True,
    validate_headers=True,
    sanitize_filenames=True,
)
validator.validate(uploaded_file)
```

## Usage

### In Django Models

The `AdUnitMedia` model automatically validates uploads in the `save()` method:

```python
# models.py
class AdUnitMedia(models.Model):
    video_file = models.FileField(upload_to="ad_unit_media/%Y/%m/")

    def save(self, *args, **kwargs):
        if self.video_file and not self.pk:
            from cw.lib.security import VideoFileValidator
            validator = VideoFileValidator()
            validator.validate(self.video_file)
        super().save(*args, **kwargs)
```

### In Django Admin Views

The bulk upload view uses the validator for all uploaded files:

```python
# admin.py
from cw.lib.security import VideoFileValidator

def bulk_upload_videos_view(self, request, object_id):
    validator = VideoFileValidator()
    video_files = request.FILES.getlist('video_files')

    # Validate all files
    results = validator.validate_multiple(video_files)

    # Separate valid and invalid
    for filename, errors in results.items():
        if errors:
            messages.error(request, f"{filename}: {', '.join(errors)}")
        else:
            # Process valid file
            ...
```

### In Django Forms

```python
from django import forms
from cw.lib.security import VideoFileValidator

class VideoUploadForm(forms.Form):
    video = forms.FileField()

    def clean_video(self):
        video = self.cleaned_data['video']
        validator = VideoFileValidator()
        validator.validate(video)
        return video
```

### Custom Validation

You can create custom validators by inheriting from `FileSecurityValidator`:

```python
from cw.lib.security.file_validation import FileSecurityValidator
from django.core.exceptions import ValidationError

class CustomVideoValidator(FileSecurityValidator):
    def _validate_impl(self, file, **kwargs):
        # Custom validation logic
        if some_condition:
            self._log_validation_failure(
                file,
                "Custom validation failed",
                severity="ERROR",
                custom_field="value"
            )
            raise ValidationError("File failed custom validation")

        self._log_validation_success(file, custom_field="value")
```

## Configuration

All security settings are in `src/cw/settings.py`:

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
VIDEO_VERIFY_MIME_CONTENT = True  # Use libmagic for MIME detection
VIDEO_VALIDATE_HEADERS = True     # Check file headers (magic bytes)
VIDEO_SANITIZE_FILENAMES = True   # Sanitize filenames

# Future: Rate Limiting
VIDEO_UPLOAD_RATE_LIMIT_ENABLED = False
VIDEO_UPLOAD_RATE_LIMIT_PER_USER = 10   # uploads per hour
VIDEO_UPLOAD_RATE_LIMIT_PER_IP = 20     # uploads per hour

# Future: Virus Scanning
VIDEO_VIRUS_SCAN_ENABLED = False
VIDEO_VIRUS_SCAN_ENDPOINT = ""  # ClamAV endpoint
```

## Security Audit Logging

All validation events are logged to `logs/tasks.log` in JSON format for security monitoring:

```json
{
  "event": "file_upload_validation_failed",
  "validator": "FileSizeValidator",
  "filename": "huge_file.mp4",
  "file_size": 1073741824,
  "content_type": "video/mp4",
  "reason": "File size (1024.0 MB) exceeds maximum (500.0 MB)",
  "severity": "WARNING"
}
```

### Log Events

- `file_upload_validation_started` - Validation begins
- `file_upload_validation_passed` - All checks passed
- `file_upload_validation_failed` - Validation failed
- `filename_sanitized` - Filename was modified
- `mime_type_mismatch` - Declared vs detected MIME mismatch

### Querying Logs with Grafana Loki

```logql
# All validation failures
{job="tasks"} | json | event="file_upload_validation_failed"

# Failed validations by specific validator
{job="tasks"} | json | validator="MimeTypeValidator" | event="file_upload_validation_failed"

# MIME type mismatches
{job="tasks"} | json | event="mime_type_mismatch"

# All security events for a specific file
{job="tasks"} | json | filename="suspicious.mp4"
```

## Testing

Comprehensive test suite at `src/cw/tvspots/tests/test_security_validation.py`:

```bash
# Run all security tests
uv run pytest src/cw/tvspots/tests/test_security_validation.py -v

# Run specific test class
uv run pytest src/cw/tvspots/tests/test_security_validation.py::FileSizeValidatorTests -v

# Run with coverage
uv run pytest src/cw/tvspots/tests/test_security_validation.py --cov=cw.lib.security
```

**Test Coverage:**
- File size validation (valid, too large, too small, empty)
- Extension validation (valid, invalid, case sensitivity)
- MIME type validation (with/without content verification, spoofing)
- File header validation (all video formats, invalid headers)
- Filename sanitization (path traversal, dangerous chars, long names)
- Composite validator (integration tests)
- Security logging (success and failure events)

## Security Best Practices

1. **Never trust file extensions** - Always use content-based validation
2. **Validate on upload** - Check files before saving to disk
3. **Sanitize filenames** - Prevent path traversal and injection attacks
4. **Log all events** - Maintain audit trail for security incidents
5. **Use multiple layers** - Don't rely on a single validation method
6. **Monitor logs** - Set up alerts for suspicious patterns
7. **Keep limits current** - Review size limits and allowed types regularly

## Threat Model

### Mitigated Threats

✅ **File Type Spoofing** - MIME verification + header validation
✅ **Path Traversal** - Filename sanitization
✅ **Malicious Executables** - Extension whitelisting + header validation
✅ **Denial of Service** - File size limits
✅ **Storage Exhaustion** - File size limits
✅ **Command Injection** - Filename sanitization (dangerous chars removed)
✅ **Malformed Filenames** - Sanitization + validation

### Future Enhancements

🔲 **Rate Limiting** - Prevent upload abuse (settings ready, implementation pending)
🔲 **Virus Scanning** - ClamAV integration (settings ready, implementation pending)
🔲 **Content Analysis** - Video codec/format validation with ffmpeg
🔲 **Duplicate Detection** - Hash-based deduplication
🔲 **Automated Cleanup** - Remove files that fail validation
🔲 **IP-based Blocking** - Block IPs with repeated violations

## Troubleshooting

### Common Issues

**Issue:** `python-magic` not found
```bash
# Install system libmagic
# macOS:
brew install libmagic

# Ubuntu/Debian:
sudo apt-get install libmagic1

# Then reinstall python-magic
uv sync
```

**Issue:** Validation too strict
```python
# Temporarily disable specific validators for testing
validator = VideoFileValidator(
    validate_headers=False,  # Skip header check
    verify_mime_content=False,  # Skip MIME content check
)
```

**Issue:** Need to allow additional formats
```python
# In settings.py, add to whitelists
VIDEO_ALLOWED_EXTENSIONS = [".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv"]
VIDEO_ALLOWED_MIME_TYPES = [..., "video/x-flv"]

# In file_validation.py FileHeaderValidator, add signature
VIDEO_SIGNATURES = {
    ...,
    "flv": [b"FLV\x01"],
}
```

## Dependencies

- **python-magic** (>=0.4.27) - MIME type detection via libmagic
- **Django** (>=6.0) - ValidationError, file upload handling
- System **libmagic** library (OS-level dependency)

## Related Documentation

- [Django File Uploads](https://docs.djangoproject.com/en/6.0/topics/http/file-uploads/)
- [python-magic Documentation](https://github.com/ahupp/python-magic)
- [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
- [Video File Formats](https://en.wikipedia.org/wiki/Video_file_format)
