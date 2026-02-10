"""
Tests for video file upload security validation.

Covers all security validators:
- File size validation
- Extension whitelisting
- MIME type verification
- File header validation
- Filename sanitization
- Composite validator
"""

import io
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from cw.lib.security import (
    FileExtensionValidator,
    FileHeaderValidator,
    FilenameSanitizer,
    FileSizeValidator,
    MimeTypeValidator,
    VideoFileValidator,
)


class FileSizeValidatorTests(TestCase):
    """Test suite for FileSizeValidator."""

    def test_valid_file_size(self):
        """Valid file size should pass validation."""
        validator = FileSizeValidator(max_size_bytes=10 * 1024 * 1024)  # 10 MB
        file = SimpleUploadedFile(
            "test.mp4",
            b"x" * (5 * 1024 * 1024),  # 5 MB
            content_type="video/mp4",
        )

        # Should not raise
        validator.validate(file)

    def test_file_too_large(self):
        """File exceeding max size should fail validation."""
        validator = FileSizeValidator(max_size_bytes=1 * 1024 * 1024)  # 1 MB
        file = SimpleUploadedFile(
            "test.mp4",
            b"x" * (2 * 1024 * 1024),  # 2 MB
            content_type="video/mp4",
        )

        with pytest.raises(ValidationError) as exc_info:
            validator.validate(file)

        assert "exceeds the maximum allowed size" in str(exc_info.value)

    def test_file_too_small(self):
        """File below minimum size should fail validation."""
        validator = FileSizeValidator(min_size_bytes=1024)  # 1 KB min
        file = SimpleUploadedFile(
            "test.mp4",
            b"x" * 512,  # 512 bytes
            content_type="video/mp4",
        )

        with pytest.raises(ValidationError) as exc_info:
            validator.validate(file)

        assert "below the minimum allowed size" in str(exc_info.value)

    def test_empty_file(self):
        """Empty file should fail validation."""
        validator = FileSizeValidator()
        file = SimpleUploadedFile("test.mp4", b"", content_type="video/mp4")

        with pytest.raises(ValidationError) as exc_info:
            validator.validate(file)

        assert "below the minimum allowed size" in str(exc_info.value)

    def test_disabled_validator(self):
        """Disabled validator should always pass."""
        validator = FileSizeValidator(max_size_bytes=1, enabled=False)
        file = SimpleUploadedFile(
            "test.mp4",
            b"x" * 1000000,  # Way too large
            content_type="video/mp4",
        )

        # Should not raise even though file is too large
        validator.validate(file)

    @override_settings(VIDEO_MAX_UPLOAD_SIZE_BYTES=5 * 1024 * 1024)
    def test_uses_settings_default(self):
        """Validator should use settings default if not specified."""
        validator = FileSizeValidator()  # No max_size_bytes specified
        file = SimpleUploadedFile(
            "test.mp4",
            b"x" * (6 * 1024 * 1024),  # 6 MB (exceeds settings default)
            content_type="video/mp4",
        )

        with pytest.raises(ValidationError):
            validator.validate(file)


class FileExtensionValidatorTests(TestCase):
    """Test suite for FileExtensionValidator."""

    def test_valid_extension(self):
        """Valid extension should pass validation."""
        validator = FileExtensionValidator(allowed_extensions={".mp4", ".mov"})
        file = SimpleUploadedFile("test.mp4", b"x", content_type="video/mp4")

        # Should not raise
        validator.validate(file)

    def test_invalid_extension(self):
        """Invalid extension should fail validation."""
        validator = FileExtensionValidator(allowed_extensions={".mp4", ".mov"})
        file = SimpleUploadedFile("test.exe", b"x", content_type="application/x-msdownload")

        with pytest.raises(ValidationError) as exc_info:
            validator.validate(file)

        assert "not allowed" in str(exc_info.value)

    def test_case_insensitive(self):
        """Extension check should be case-insensitive."""
        validator = FileExtensionValidator(allowed_extensions={".mp4"})
        file = SimpleUploadedFile("test.MP4", b"x", content_type="video/mp4")

        # Should not raise
        validator.validate(file)

    def test_no_extension(self):
        """File without extension should fail validation."""
        validator = FileExtensionValidator(allowed_extensions={".mp4"})
        file = SimpleUploadedFile("test", b"x", content_type="video/mp4")

        with pytest.raises(ValidationError):
            validator.validate(file)

    def test_double_extension(self):
        """File with double extension should validate on final extension."""
        validator = FileExtensionValidator(allowed_extensions={".mp4"})
        file = SimpleUploadedFile("test.tar.mp4", b"x", content_type="video/mp4")

        # Should not raise (validates .mp4)
        validator.validate(file)

    @override_settings(VIDEO_ALLOWED_EXTENSIONS=[".mp4", ".webm"])
    def test_uses_settings_default(self):
        """Validator should use settings default if not specified."""
        validator = FileExtensionValidator()  # No allowed_extensions specified
        file = SimpleUploadedFile("test.avi", b"x", content_type="video/x-msvideo")

        with pytest.raises(ValidationError):
            validator.validate(file)


class MimeTypeValidatorTests(TestCase):
    """Test suite for MimeTypeValidator."""

    def test_valid_declared_mime_no_verification(self):
        """Valid declared MIME type should pass (no content verification)."""
        validator = MimeTypeValidator(
            allowed_mime_types={"video/mp4"},
            verify_content=False,
        )
        file = SimpleUploadedFile("test.mp4", b"x" * 1024, content_type="video/mp4")

        # Should not raise
        validator.validate(file)

    def test_invalid_declared_mime_no_verification(self):
        """Invalid declared MIME type should fail (no content verification)."""
        validator = MimeTypeValidator(
            allowed_mime_types={"video/mp4"},
            verify_content=False,
        )
        file = SimpleUploadedFile(
            "test.exe",
            b"x" * 1024,
            content_type="application/x-msdownload",
        )

        with pytest.raises(ValidationError) as exc_info:
            validator.validate(file)

        assert "not allowed" in str(exc_info.value)

    @patch("cw.lib.security.file_validation.magic.Magic")
    def test_valid_detected_mime_with_verification(self, mock_magic_class):
        """Valid detected MIME type should pass (with content verification)."""
        mock_magic = Mock()
        mock_magic.from_buffer.return_value = "video/mp4"
        mock_magic_class.return_value = mock_magic

        validator = MimeTypeValidator(
            allowed_mime_types={"video/mp4"},
            verify_content=True,
        )
        file = SimpleUploadedFile("test.mp4", b"x" * 1024, content_type="video/mp4")

        # Should not raise
        validator.validate(file)

    @patch("cw.lib.security.file_validation.magic.Magic")
    def test_invalid_detected_mime_with_verification(self, mock_magic_class):
        """Invalid detected MIME type should fail (with content verification)."""
        mock_magic = Mock()
        mock_magic.from_buffer.return_value = "application/x-executable"
        mock_magic_class.return_value = mock_magic

        validator = MimeTypeValidator(
            allowed_mime_types={"video/mp4"},
            verify_content=True,
        )
        file = SimpleUploadedFile("test.mp4", b"MZ\x90\x00" * 256, content_type="video/mp4")

        with pytest.raises(ValidationError) as exc_info:
            validator.validate(file)

        assert "not allowed" in str(exc_info.value)

    @patch("cw.lib.security.file_validation.magic.Magic")
    def test_mime_mismatch_warning(self, mock_magic_class):
        """MIME mismatch should log warning but still pass if detected type is allowed."""
        mock_magic = Mock()
        mock_magic.from_buffer.return_value = "video/quicktime"
        mock_magic_class.return_value = mock_magic

        validator = MimeTypeValidator(
            allowed_mime_types={"video/mp4", "video/quicktime"},
            verify_content=True,
        )
        file = SimpleUploadedFile("test.mp4", b"x" * 1024, content_type="video/mp4")

        # Should not raise (both types allowed, just different)
        with self.assertLogs("cw.lib.security.file_validation", level="WARNING") as logs:
            validator.validate(file)

        # Check that warning was logged
        assert any("MIME type mismatch" in log for log in logs.output)

    @patch("cw.lib.security.file_validation.magic.Magic")
    def test_magic_detection_error(self, mock_magic_class):
        """Error during MIME detection should fail validation."""
        mock_magic = Mock()
        mock_magic.from_buffer.side_effect = Exception("libmagic error")
        mock_magic_class.return_value = mock_magic

        validator = MimeTypeValidator(verify_content=True)
        file = SimpleUploadedFile("test.mp4", b"x" * 1024, content_type="video/mp4")

        with pytest.raises(ValidationError) as exc_info:
            validator.validate(file)

        assert "Unable to verify file type" in str(exc_info.value)


class FileHeaderValidatorTests(TestCase):
    """Test suite for FileHeaderValidator."""

    def test_valid_mp4_header(self):
        """Valid MP4 file header should pass validation."""
        validator = FileHeaderValidator()
        # MP4 file signature (ftyp box)
        mp4_header = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 1000
        file = SimpleUploadedFile("test.mp4", mp4_header, content_type="video/mp4")

        # Should not raise
        validator.validate(file)

    def test_valid_avi_header(self):
        """Valid AVI file header should pass validation."""
        validator = FileHeaderValidator()
        # AVI file signature (RIFF header)
        avi_header = b"RIFF" + b"\x00" * 1000
        file = SimpleUploadedFile("test.avi", avi_header, content_type="video/x-msvideo")

        # Should not raise
        validator.validate(file)

    def test_valid_mkv_header(self):
        """Valid MKV file header should pass validation."""
        validator = FileHeaderValidator()
        # Matroska/MKV file signature (EBML header)
        mkv_header = b"\x1A\x45\xDF\xA3" + b"\x00" * 1000
        file = SimpleUploadedFile("test.mkv", mkv_header, content_type="video/x-matroska")

        # Should not raise
        validator.validate(file)

    def test_invalid_header(self):
        """Invalid file header should fail validation."""
        validator = FileHeaderValidator()
        # Executable file header (MZ signature)
        exe_header = b"MZ\x90\x00" + b"\x00" * 1000
        file = SimpleUploadedFile("test.mp4", exe_header, content_type="video/mp4")

        with pytest.raises(ValidationError) as exc_info:
            validator.validate(file)

        assert "does not appear to be a valid video file" in str(exc_info.value)

    def test_random_bytes_header(self):
        """Random bytes should fail validation."""
        validator = FileHeaderValidator()
        file = SimpleUploadedFile("test.mp4", b"Random content!", content_type="video/mp4")

        with pytest.raises(ValidationError) as exc_info:
            validator.validate(file)

        assert "not recognized" in str(exc_info.value)

    def test_empty_file_header(self):
        """Empty file should fail validation."""
        validator = FileHeaderValidator()
        file = SimpleUploadedFile("test.mp4", b"", content_type="video/mp4")

        with pytest.raises(ValidationError):
            validator.validate(file)


class FilenameSanitizerTests(TestCase):
    """Test suite for FilenameSanitizer."""

    def test_clean_filename_unchanged(self):
        """Clean filename should remain unchanged."""
        sanitizer = FilenameSanitizer()
        file = SimpleUploadedFile("test_video.mp4", b"x", content_type="video/mp4")
        original_name = file.name

        sanitizer.validate(file)

        assert file.name == original_name

    def test_path_traversal_removed(self):
        """Path traversal attempts should be removed."""
        sanitizer = FilenameSanitizer(remove_path_components=True)
        file = SimpleUploadedFile(
            "../../../etc/passwd.mp4",
            b"x",
            content_type="video/mp4",
        )

        sanitizer.validate(file)

        # Should only keep the basename
        assert file.name == "passwd.mp4"

    def test_windows_path_removed(self):
        """Windows path should be removed."""
        sanitizer = FilenameSanitizer(remove_path_components=True)
        file = SimpleUploadedFile(
            r"C:\Windows\System32\malware.mp4",
            b"x",
            content_type="video/mp4",
        )

        sanitizer.validate(file)

        # Should only keep the basename
        assert file.name == "malware.mp4"

    def test_spaces_replaced(self):
        """Spaces should be replaced with underscores."""
        sanitizer = FilenameSanitizer(replace_spaces=True)
        file = SimpleUploadedFile("test video file.mp4", b"x", content_type="video/mp4")

        sanitizer.validate(file)

        assert file.name == "test_video_file.mp4"

    def test_lowercase_conversion(self):
        """Filename should be converted to lowercase if enabled."""
        sanitizer = FilenameSanitizer(lowercase=True)
        file = SimpleUploadedFile("Test_Video.MP4", b"x", content_type="video/mp4")

        sanitizer.validate(file)

        assert file.name == "test_video.mp4"

    def test_dangerous_characters_removed(self):
        """Dangerous characters should be removed."""
        sanitizer = FilenameSanitizer()
        file = SimpleUploadedFile("test<>:|?*.mp4", b"x", content_type="video/mp4")

        sanitizer.validate(file)

        # Dangerous characters removed
        assert "<" not in file.name
        assert ">" not in file.name
        assert ":" not in file.name
        assert "|" not in file.name
        assert "?" not in file.name
        assert "*" not in file.name

    def test_control_characters_removed(self):
        """Control characters should be removed."""
        sanitizer = FilenameSanitizer()
        file = SimpleUploadedFile("test\x00\x01\x1f.mp4", b"x", content_type="video/mp4")

        sanitizer.validate(file)

        # Control characters removed
        assert "\x00" not in file.name
        assert "\x01" not in file.name
        assert "\x1f" not in file.name

    def test_long_filename_truncated(self):
        """Very long filenames should be truncated."""
        sanitizer = FilenameSanitizer()
        long_name = "a" * 300 + ".mp4"
        file = SimpleUploadedFile(long_name, b"x", content_type="video/mp4")

        sanitizer.validate(file)

        # Should be truncated to max length (255) + extension
        assert len(file.name) <= 255 + len(".mp4")

    def test_empty_name_replaced(self):
        """Empty name after sanitization should be replaced with default."""
        # Disable replace_spaces to avoid interference
        sanitizer = FilenameSanitizer(replace_spaces=False)
        # Use control characters that get removed, leaving empty name
        # \x00\x01\x02.mp4 → .mp4 after control char removal → empty name after strip
        file = SimpleUploadedFile("\x00\x01\x02.mp4", b"x", content_type="video/mp4")

        sanitizer.validate(file)

        # After removing control chars and stripping, name should be "unnamed"
        assert file.name == "unnamed.mp4"


class VideoFileValidatorTests(TestCase):
    """Test suite for composite VideoFileValidator."""

    @patch("cw.lib.security.file_validation.magic.Magic")
    def test_valid_video_file_passes_all_checks(self, mock_magic_class):
        """Valid video file should pass all validations."""
        mock_magic = Mock()
        mock_magic.from_buffer.return_value = "video/mp4"
        mock_magic_class.return_value = mock_magic

        validator = VideoFileValidator(
            max_size_bytes=10 * 1024 * 1024,
            allowed_extensions={".mp4"},
            allowed_mime_types={"video/mp4"},
        )

        # Valid MP4 file
        mp4_header = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 1000
        file = SimpleUploadedFile("test.mp4", mp4_header, content_type="video/mp4")

        # Should not raise
        validator.validate(file)

    def test_oversized_file_fails(self):
        """Oversized file should fail validation."""
        validator = VideoFileValidator(max_size_bytes=1 * 1024 * 1024)  # 1 MB

        file = SimpleUploadedFile(
            "large.mp4",
            b"x" * (2 * 1024 * 1024),  # 2 MB
            content_type="video/mp4",
        )

        with pytest.raises(ValidationError):
            validator.validate(file)

    def test_wrong_extension_fails(self):
        """Wrong extension should fail validation."""
        validator = VideoFileValidator(allowed_extensions={".mp4"})

        file = SimpleUploadedFile("test.exe", b"x" * 1024, content_type="video/mp4")

        with pytest.raises(ValidationError):
            validator.validate(file)

    @patch("cw.lib.security.file_validation.magic.Magic")
    def test_spoofed_file_fails_header_check(self, mock_magic_class):
        """File with spoofed extension but wrong header should fail."""
        mock_magic = Mock()
        mock_magic.from_buffer.return_value = "video/mp4"
        mock_magic_class.return_value = mock_magic

        validator = VideoFileValidator(
            allowed_extensions={".mp4"},
            validate_headers=True,
        )

        # File with .mp4 extension but executable header
        exe_header = b"MZ\x90\x00" + b"\x00" * 1000
        file = SimpleUploadedFile("malware.mp4", exe_header, content_type="video/mp4")

        with pytest.raises(ValidationError):
            validator.validate(file)

    def test_filename_gets_sanitized(self):
        """Filename should be sanitized by default."""
        validator = VideoFileValidator(
            max_size_bytes=10 * 1024 * 1024,
            sanitize_filenames=True,
            validate_headers=False,  # Skip header check for this test
            verify_mime_content=False,  # Skip MIME content check
        )

        file = SimpleUploadedFile(
            "../../../dangerous file.mp4",
            b"x" * 1024,
            content_type="video/mp4",
        )

        # Should not raise, but filename should be sanitized
        validator.validate(file)

        assert file.name == "dangerous_file.mp4"

    def test_validate_multiple_files(self):
        """Validate multiple files and get results dict."""
        validator = VideoFileValidator(
            max_size_bytes=10 * 1024 * 1024,
            allowed_extensions={".mp4"},
            validate_headers=False,
            verify_mime_content=False,
        )

        files = [
            SimpleUploadedFile("valid.mp4", b"x" * 1024, content_type="video/mp4"),
            SimpleUploadedFile("toolarge.mp4", b"x" * (20 * 1024 * 1024), content_type="video/mp4"),
            SimpleUploadedFile("wrong.exe", b"x" * 1024, content_type="application/x-msdownload"),
        ]

        results = validator.validate_multiple(files)

        # Valid file should have no errors
        assert results["valid.mp4"] == []

        # Too large file should have error
        assert len(results["toolarge.mp4"]) > 0
        assert any("exceeds" in err for err in results["toolarge.mp4"])

        # Wrong extension should have error
        assert len(results["wrong.exe"]) > 0
        assert any("not allowed" in err for err in results["wrong.exe"])

    @override_settings(
        VIDEO_MAX_UPLOAD_SIZE_BYTES=5 * 1024 * 1024,
        VIDEO_ALLOWED_EXTENSIONS=[".mp4", ".webm"],
        VIDEO_ALLOWED_MIME_TYPES=["video/mp4", "video/webm"],
        VIDEO_VERIFY_MIME_CONTENT=False,
        VIDEO_VALIDATE_HEADERS=False,
    )
    def test_uses_all_settings_defaults(self):
        """Validator should use all settings defaults when not specified."""
        # Create validator without any parameters
        validator = VideoFileValidator()

        # File exceeds settings max size
        file = SimpleUploadedFile(
            "test.mp4",
            b"x" * (6 * 1024 * 1024),
            content_type="video/mp4",
        )

        with pytest.raises(ValidationError):
            validator.validate(file)

    def test_disabled_validator_skips_all_checks(self):
        """Disabled validator should skip all checks."""
        validator = VideoFileValidator(
            max_size_bytes=1,
            allowed_extensions={".mp4"},
            enable_all=False,
        )

        # File that would fail all checks
        file = SimpleUploadedFile(
            "huge_malware.exe",
            b"MZ\x90\x00" * 100000,
            content_type="application/x-msdownload",
        )

        # Should not raise because all validators are disabled
        validator.validate(file)


class SecurityLoggingTests(TestCase):
    """Test security audit logging."""

    def test_validation_failure_logged(self):
        """Validation failures should be logged for audit."""
        validator = FileSizeValidator(max_size_bytes=1024)
        file = SimpleUploadedFile("test.mp4", b"x" * 2048, content_type="video/mp4")

        with self.assertLogs("cw.lib.security.file_validation", level="WARNING") as logs:
            with pytest.raises(ValidationError):
                validator.validate(file)

        # Check that failure was logged
        assert any("File validation failed" in log for log in logs.output)

    def test_validation_success_logged(self):
        """Validation successes should be logged for audit."""
        validator = FileSizeValidator(max_size_bytes=10 * 1024 * 1024)
        file = SimpleUploadedFile("test.mp4", b"x" * 1024, content_type="video/mp4")

        with self.assertLogs("cw.lib.security.file_validation", level="INFO") as logs:
            validator.validate(file)

        # Check that success was logged
        assert any("File validation passed" in log for log in logs.output)

    @patch("cw.lib.security.file_validation.magic.Magic")
    def test_composite_validator_logs_all_stages(self, mock_magic_class):
        """Composite validator should log all validation stages."""
        mock_magic = Mock()
        mock_magic.from_buffer.return_value = "video/mp4"
        mock_magic_class.return_value = mock_magic

        validator = VideoFileValidator(
            max_size_bytes=10 * 1024 * 1024,
            allowed_extensions={".mp4"},
            verify_mime_content=True,
            validate_headers=False,
        )

        mp4_content = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 1000
        file = SimpleUploadedFile("test.mp4", mp4_content, content_type="video/mp4")

        with self.assertLogs("cw.lib.security.file_validation", level="INFO") as logs:
            validator.validate(file)

        # Should have logs from multiple validators
        log_output = "\n".join(logs.output)
        assert "FileSizeValidator" in log_output
        assert "FileExtensionValidator" in log_output
        assert "MimeTypeValidator" in log_output
