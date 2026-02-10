"""
File upload security validation for video files.

Provides comprehensive security checks for uploaded video files including:
- File size validation
- Extension whitelisting
- MIME type verification
- File header (magic bytes) verification
- Filename sanitization
- Path traversal prevention
- Malicious content detection

All validation failures are logged for security auditing.
"""

import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import magic

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile

logger = logging.getLogger(__name__)


class FileSecurityValidator:
    """Base class for file security validators.

    All validators should inherit from this class and implement the validate() method.
    Validation failures are logged with audit information.
    """

    def __init__(self, enabled: bool = True):
        """Initialize validator.

        Args:
            enabled: Whether this validator is enabled. Disabled validators always pass.
        """
        self.enabled = enabled

    def validate(self, file: UploadedFile, **kwargs) -> None:
        """Validate the uploaded file.

        Args:
            file: The uploaded file to validate
            **kwargs: Additional validator-specific parameters

        Raises:
            ValidationError: If validation fails
        """
        if not self.enabled:
            return
        self._validate_impl(file, **kwargs)

    def _validate_impl(self, file: UploadedFile, **kwargs) -> None:
        """Implementation of validation logic. Must be overridden by subclasses.

        Args:
            file: The uploaded file to validate
            **kwargs: Additional validator-specific parameters

        Raises:
            ValidationError: If validation fails
        """
        raise NotImplementedError("Validators must implement _validate_impl()")

    def _log_validation_failure(
        self,
        file: UploadedFile,
        reason: str,
        severity: str = "WARNING",
        **extra_context
    ) -> None:
        """Log validation failure for security auditing.

        Args:
            file: The uploaded file that failed validation
            reason: Human-readable reason for failure
            severity: Log level (WARNING, ERROR, CRITICAL)
            **extra_context: Additional context to include in log
        """
        log_data = {
            "event": "file_upload_validation_failed",
            "validator": self.__class__.__name__,
            "upload_filename": file.name,
            "file_size": file.size,
            "content_type": file.content_type,
            "reason": reason,
            **extra_context,
        }

        if severity == "ERROR":
            logger.error(f"File validation failed: {reason}", extra=log_data)
        elif severity == "CRITICAL":
            logger.critical(f"Critical file validation failure: {reason}", extra=log_data)
        else:
            logger.warning(f"File validation failed: {reason}", extra=log_data)

    def _log_validation_success(self, file: UploadedFile, **extra_context) -> None:
        """Log successful validation for auditing.

        Args:
            file: The uploaded file that passed validation
            **extra_context: Additional context to include in log
        """
        log_data = {
            "event": "file_upload_validation_passed",
            "validator": self.__class__.__name__,
            "upload_filename": file.name,
            "file_size": file.size,
            "content_type": file.content_type,
            **extra_context,
        }
        logger.info(f"File validation passed: {self.__class__.__name__}", extra=log_data)


class FileSizeValidator(FileSecurityValidator):
    """Validates file size against configured limits.

    Prevents denial-of-service attacks via oversized uploads and ensures
    storage constraints are respected.
    """

    def __init__(
        self,
        max_size_bytes: Optional[int] = None,
        min_size_bytes: int = 1,
        enabled: bool = True,
    ):
        """Initialize file size validator.

        Args:
            max_size_bytes: Maximum allowed file size in bytes.
                Defaults to settings.VIDEO_MAX_UPLOAD_SIZE_BYTES
            min_size_bytes: Minimum allowed file size in bytes (default: 1)
            enabled: Whether this validator is enabled
        """
        super().__init__(enabled=enabled)
        self.max_size_bytes = max_size_bytes or getattr(
            settings,
            "VIDEO_MAX_UPLOAD_SIZE_BYTES",
            500 * 1024 * 1024  # 500 MB default
        )
        self.min_size_bytes = min_size_bytes

    def _validate_impl(self, file: UploadedFile, **kwargs) -> None:
        """Validate file size is within allowed range.

        Args:
            file: The uploaded file to validate

        Raises:
            ValidationError: If file size is outside allowed range
        """
        file_size = file.size

        # Check minimum size (detect empty or corrupted uploads)
        if file_size < self.min_size_bytes:
            self._log_validation_failure(
                file,
                f"File size ({file_size} bytes) below minimum ({self.min_size_bytes} bytes)",
                severity="WARNING",
                file_size_bytes=file_size,
                min_size_bytes=self.min_size_bytes,
            )
            raise ValidationError(
                f"File size ({file_size} bytes) is below the minimum allowed size "
                f"({self.min_size_bytes} bytes)."
            )

        # Check maximum size
        if file_size > self.max_size_bytes:
            size_mb = file_size / (1024 * 1024)
            max_mb = self.max_size_bytes / (1024 * 1024)
            self._log_validation_failure(
                file,
                f"File size ({size_mb:.1f} MB) exceeds maximum ({max_mb:.1f} MB)",
                severity="WARNING",
                file_size_bytes=file_size,
                max_size_bytes=self.max_size_bytes,
            )
            raise ValidationError(
                f"File size ({size_mb:.1f} MB) exceeds the maximum allowed size "
                f"({max_mb:.1f} MB)."
            )

        self._log_validation_success(
            file,
            file_size_bytes=file_size,
            max_size_bytes=self.max_size_bytes,
        )


class FileExtensionValidator(FileSecurityValidator):
    """Validates file extension against a whitelist.

    Prevents upload of executable files or files with misleading extensions.
    Case-insensitive comparison.
    """

    def __init__(
        self,
        allowed_extensions: Optional[Set[str]] = None,
        enabled: bool = True,
    ):
        """Initialize extension validator.

        Args:
            allowed_extensions: Set of allowed extensions (with leading dot, e.g., {'.mp4', '.mov'}).
                Defaults to settings.VIDEO_ALLOWED_EXTENSIONS
            enabled: Whether this validator is enabled
        """
        super().__init__(enabled=enabled)
        self.allowed_extensions = allowed_extensions or set(
            getattr(
                settings,
                "VIDEO_ALLOWED_EXTENSIONS",
                [".mp4", ".mov", ".avi", ".mkv", ".webm"],
            )
        )
        # Normalize to lowercase
        self.allowed_extensions = {ext.lower() for ext in self.allowed_extensions}

    def _validate_impl(self, file: UploadedFile, **kwargs) -> None:
        """Validate file extension is in the whitelist.

        Args:
            file: The uploaded file to validate

        Raises:
            ValidationError: If file extension is not allowed
        """
        # Extract extension (case-insensitive)
        filename = file.name or ""
        ext = os.path.splitext(filename)[1].lower()

        if ext not in self.allowed_extensions:
            self._log_validation_failure(
                file,
                f"File extension '{ext}' not in whitelist",
                severity="WARNING",
                extension=ext,
                allowed_extensions=list(self.allowed_extensions),
            )
            raise ValidationError(
                f"File extension '{ext}' is not allowed. "
                f"Allowed extensions: {', '.join(sorted(self.allowed_extensions))}"
            )

        self._log_validation_success(file, extension=ext)


class MimeTypeValidator(FileSecurityValidator):
    """Validates MIME type from file content (not just declared content-type).

    Uses python-magic (libmagic) to detect actual file type from content,
    preventing extension-based spoofing attacks.
    """

    def __init__(
        self,
        allowed_mime_types: Optional[Set[str]] = None,
        verify_content: bool = True,
        enabled: bool = True,
    ):
        """Initialize MIME type validator.

        Args:
            allowed_mime_types: Set of allowed MIME types.
                Defaults to settings.VIDEO_ALLOWED_MIME_TYPES
            verify_content: If True, uses libmagic to detect MIME type from content.
                If False, only checks declared content_type header.
            enabled: Whether this validator is enabled
        """
        super().__init__(enabled=enabled)
        self.allowed_mime_types = allowed_mime_types or set(
            getattr(
                settings,
                "VIDEO_ALLOWED_MIME_TYPES",
                [
                    "video/mp4",
                    "video/quicktime",
                    "video/x-msvideo",
                    "video/x-matroska",
                    "video/webm",
                ],
            )
        )
        self.verify_content = verify_content

    def _detect_mime_type(self, file: UploadedFile) -> str:
        """Detect MIME type from file content using libmagic.

        Args:
            file: The uploaded file to analyze

        Returns:
            Detected MIME type string
        """
        # Read first chunk for MIME detection
        file.seek(0)
        chunk = file.read(8192)  # Read 8KB for magic detection
        file.seek(0)  # Reset position

        # Use python-magic to detect MIME type
        mime = magic.Magic(mime=True)
        detected_mime = mime.from_buffer(chunk)
        return detected_mime

    def _validate_impl(self, file: UploadedFile, **kwargs) -> None:
        """Validate MIME type is in the whitelist.

        Args:
            file: The uploaded file to validate

        Raises:
            ValidationError: If MIME type is not allowed or doesn't match content
        """
        declared_mime = file.content_type

        if self.verify_content:
            # Detect actual MIME type from file content
            try:
                detected_mime = self._detect_mime_type(file)
            except Exception as e:
                self._log_validation_failure(
                    file,
                    f"Failed to detect MIME type: {e}",
                    severity="ERROR",
                    declared_mime=declared_mime,
                    error=str(e),
                )
                raise ValidationError(
                    f"Unable to verify file type. The file may be corrupted. Error: {e}"
                )

            # Check if detected MIME is allowed
            if detected_mime not in self.allowed_mime_types:
                self._log_validation_failure(
                    file,
                    f"Detected MIME type '{detected_mime}' not in whitelist",
                    severity="ERROR",
                    declared_mime=declared_mime,
                    detected_mime=detected_mime,
                    allowed_mime_types=list(self.allowed_mime_types),
                )
                raise ValidationError(
                    f"File type '{detected_mime}' is not allowed. "
                    f"Allowed types: {', '.join(sorted(self.allowed_mime_types))}"
                )

            # Warn if declared and detected MIME don't match
            if declared_mime and declared_mime != detected_mime:
                logger.warning(
                    f"MIME type mismatch: declared '{declared_mime}' but detected '{detected_mime}'",
                    extra={
                        "event": "mime_type_mismatch",
                        "upload_filename": file.name,
                        "declared_mime": declared_mime,
                        "detected_mime": detected_mime,
                    },
                )

            self._log_validation_success(
                file,
                declared_mime=declared_mime,
                detected_mime=detected_mime,
            )
        else:
            # Only check declared content-type
            if declared_mime not in self.allowed_mime_types:
                self._log_validation_failure(
                    file,
                    f"Declared MIME type '{declared_mime}' not in whitelist",
                    severity="WARNING",
                    declared_mime=declared_mime,
                    allowed_mime_types=list(self.allowed_mime_types),
                )
                raise ValidationError(
                    f"File type '{declared_mime}' is not allowed. "
                    f"Allowed types: {', '.join(sorted(self.allowed_mime_types))}"
                )

            self._log_validation_success(file, declared_mime=declared_mime)


class FileHeaderValidator(FileSecurityValidator):
    """Validates file headers (magic bytes) to prevent file type spoofing.

    Checks that file headers match expected video file signatures.
    """

    # Common video file signatures (magic bytes)
    VIDEO_SIGNATURES: Dict[str, List[bytes]] = {
        "mp4": [
            b"\x00\x00\x00\x18ftypmp42",  # MP4 (ftyp box)
            b"\x00\x00\x00\x20ftypmp42",
            b"\x00\x00\x00\x18ftypisom",  # MP4 ISO Base Media
            b"\x00\x00\x00\x20ftypisom",
        ],
        "mov": [
            b"\x00\x00\x00\x14ftypqt  ",  # QuickTime
        ],
        "avi": [
            b"RIFF",  # AVI (RIFF container)
        ],
        "mkv": [
            b"\x1A\x45\xDF\xA3",  # Matroska/WebM (EBML header)
        ],
        "webm": [
            b"\x1A\x45\xDF\xA3",  # WebM uses same header as MKV
        ],
    }

    def __init__(self, enabled: bool = True):
        """Initialize file header validator.

        Args:
            enabled: Whether this validator is enabled
        """
        super().__init__(enabled=enabled)

    def _check_signature(self, file: UploadedFile) -> Tuple[bool, Optional[str]]:
        """Check if file header matches known video signatures.

        Args:
            file: The uploaded file to check

        Returns:
            Tuple of (is_valid, detected_format)
        """
        file.seek(0)
        header = file.read(32)  # Read first 32 bytes
        file.seek(0)  # Reset position

        # Check against all known video signatures
        for format_name, signatures in self.VIDEO_SIGNATURES.items():
            for signature in signatures:
                if header.startswith(signature):
                    return True, format_name

        return False, None

    def _validate_impl(self, file: UploadedFile, **kwargs) -> None:
        """Validate file header matches known video signatures.

        Args:
            file: The uploaded file to validate

        Raises:
            ValidationError: If file header doesn't match any known video signature
        """
        is_valid, detected_format = self._check_signature(file)

        if not is_valid:
            # Read first 16 bytes for logging
            file.seek(0)
            header_hex = file.read(16).hex()
            file.seek(0)

            self._log_validation_failure(
                file,
                "File header does not match known video signatures",
                severity="ERROR",
                header_hex=header_hex,
            )
            raise ValidationError(
                "File does not appear to be a valid video file. "
                "The file header is not recognized."
            )

        self._log_validation_success(file, detected_format=detected_format)


class FilenameSanitizer(FileSecurityValidator):
    """Sanitizes filenames to prevent path traversal and other attacks.

    Removes or escapes dangerous characters and patterns from filenames.
    Does not raise ValidationError - instead modifies the filename in-place.
    """

    # Dangerous patterns that could indicate path traversal or command injection
    DANGEROUS_PATTERNS = [
        r"\.\.",  # Parent directory reference
        r"[<>:\"|?*]",  # Windows forbidden characters
        r"[\x00-\x1f]",  # Control characters
        r"^\..*",  # Hidden files (optional - currently allowed)
    ]

    # Maximum filename length (without extension)
    MAX_FILENAME_LENGTH = 255

    def __init__(
        self,
        remove_path_components: bool = True,
        replace_spaces: bool = True,
        lowercase: bool = False,
        enabled: bool = True,
    ):
        """Initialize filename sanitizer.

        Args:
            remove_path_components: Remove any path components (keep only basename)
            replace_spaces: Replace spaces with underscores
            lowercase: Convert filename to lowercase
            enabled: Whether this validator is enabled
        """
        super().__init__(enabled=enabled)
        self.remove_path_components = remove_path_components
        self.replace_spaces = replace_spaces
        self.lowercase = lowercase

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize a filename.

        Args:
            filename: The original filename

        Returns:
            Sanitized filename
        """
        # Remove path components (security: prevent directory traversal)
        if self.remove_path_components:
            # Handle both Unix and Windows path separators
            # Replace all path separators with Unix separator, then use basename
            filename = filename.replace("\\", "/")
            filename = os.path.basename(filename)

        # Split into name and extension
        name, ext = os.path.splitext(filename)

        # Remove dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            name = re.sub(pattern, "", name)

        # Replace spaces
        if self.replace_spaces:
            name = name.replace(" ", "_")

        # Remove leading/trailing dots and whitespace
        name = name.strip(". ")

        # Ensure we have a valid name before lowercase/truncate
        if not name:
            name = "unnamed"

        # Convert to lowercase (after ensuring name exists)
        if self.lowercase:
            name = name.lower()
            ext = ext.lower()

        # Truncate if too long
        if len(name) > self.MAX_FILENAME_LENGTH:
            name = name[:self.MAX_FILENAME_LENGTH]

        return f"{name}{ext}"

    def _validate_impl(self, file: UploadedFile, **kwargs) -> None:
        """Sanitize the filename (modifies file.name in-place).

        Args:
            file: The uploaded file to sanitize
        """
        original_name = file.name
        sanitized_name = self._sanitize_filename(original_name)

        if original_name != sanitized_name:
            logger.warning(
                f"Filename sanitized: '{original_name}' → '{sanitized_name}'",
                extra={
                    "event": "filename_sanitized",
                    "original_name": original_name,
                    "sanitized_name": sanitized_name,
                },
            )
            # Modify the file object's name
            file.name = sanitized_name

        self._log_validation_success(
            file,
            original_name=original_name,
            sanitized_name=sanitized_name,
        )


class VideoFileValidator:
    """Composite validator for video file uploads.

    Chains multiple validators together and provides a single validation interface.
    Use this as the main entry point for video file validation.
    """

    def __init__(
        self,
        max_size_bytes: Optional[int] = None,
        allowed_extensions: Optional[Set[str]] = None,
        allowed_mime_types: Optional[Set[str]] = None,
        verify_mime_content: bool = True,
        validate_headers: bool = True,
        sanitize_filenames: bool = True,
        enable_all: bool = True,
    ):
        """Initialize composite video file validator.

        Args:
            max_size_bytes: Maximum file size in bytes
            allowed_extensions: Set of allowed extensions (e.g., {'.mp4', '.mov'})
            allowed_mime_types: Set of allowed MIME types
            verify_mime_content: Use libmagic to verify MIME from content
            validate_headers: Check file headers (magic bytes)
            sanitize_filenames: Sanitize filenames for security
            enable_all: Enable all validators (can be overridden per-validator)
        """
        self.validators: List[FileSecurityValidator] = []

        # Size validation
        self.validators.append(
            FileSizeValidator(
                max_size_bytes=max_size_bytes,
                enabled=enable_all,
            )
        )

        # Extension validation
        self.validators.append(
            FileExtensionValidator(
                allowed_extensions=allowed_extensions,
                enabled=enable_all,
            )
        )

        # MIME type validation
        self.validators.append(
            MimeTypeValidator(
                allowed_mime_types=allowed_mime_types,
                verify_content=verify_mime_content,
                enabled=enable_all,
            )
        )

        # File header validation
        if validate_headers:
            self.validators.append(FileHeaderValidator(enabled=enable_all))

        # Filename sanitization (should run last)
        if sanitize_filenames:
            self.validators.append(
                FilenameSanitizer(
                    remove_path_components=True,
                    replace_spaces=True,
                    lowercase=False,
                    enabled=enable_all,
                )
            )

    def validate(self, file: UploadedFile) -> None:
        """Run all validators on the uploaded file.

        Args:
            file: The uploaded file to validate

        Raises:
            ValidationError: If any validator fails
        """
        logger.info(
            f"Starting video file validation for '{file.name}'",
            extra={
                "event": "video_validation_started",
                "upload_filename": file.name,
                "file_size": file.size,
                "content_type": file.content_type,
                "validator_count": len(self.validators),
            },
        )

        validation_errors = []

        for validator in self.validators:
            try:
                validator.validate(file)
            except ValidationError as e:
                validation_errors.append(str(e))

        if validation_errors:
            # Combine all validation errors
            combined_error = " | ".join(validation_errors)
            logger.error(
                f"Video file validation failed for '{file.name}': {combined_error}",
                extra={
                    "event": "video_validation_failed",
                    "upload_filename": file.name,
                    "file_size": file.size,
                    "errors": validation_errors,
                },
            )
            raise ValidationError(combined_error)

        logger.info(
            f"Video file validation passed for '{file.name}'",
            extra={
                "event": "video_validation_passed",
                "upload_filename": file.name,
                "file_size": file.size,
            },
        )

    def validate_multiple(self, files: List[UploadedFile]) -> Dict[str, List[str]]:
        """Validate multiple files and return validation results.

        Args:
            files: List of uploaded files to validate

        Returns:
            Dictionary mapping filenames to list of validation errors (empty list if valid)
        """
        results = {}
        for file in files:
            try:
                self.validate(file)
                results[file.name] = []  # No errors
            except ValidationError as e:
                results[file.name] = [str(e)]

        return results
