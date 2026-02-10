"""
Unit tests for video analysis utilities.

Tests cover:
- Video metadata extraction (PyAV)
- Scene detection (PySceneDetect)
- Audio transcription (Whisper)

Note: These tests use mocks to avoid requiring actual video files.
Integration tests with real video files should be run separately.
"""

from unittest.mock import MagicMock, Mock, patch

from django.test import TestCase


class VideoMetadataExtractionTestCase(TestCase):
    """Test extract_video_metadata utility."""

    @patch("cw.lib.video_analysis.metadata.av.open")
    @patch("cw.lib.video_analysis.metadata.os.path.exists")
    @patch("cw.lib.video_analysis.metadata.os.path.getsize")
    def test_extract_metadata_success(self, mock_getsize, mock_exists, mock_av_open):
        """Test successful metadata extraction."""
        from cw.lib.video_analysis import extract_video_metadata

        # Mock file exists and size
        mock_exists.return_value = True
        mock_getsize.return_value = 5242880  # 5 MB

        # Mock video stream
        video_stream = Mock()
        video_stream.width = 1920
        video_stream.height = 1080
        video_stream.average_rate = 29.97
        video_stream.duration = 900  # 30 seconds at 30fps time base
        video_stream.time_base = 1 / 30

        # Mock audio stream
        audio_stream = Mock()
        audio_stream.channels = 2
        audio_stream.rate = 48000

        # Mock container
        container = MagicMock()
        container.streams.video = [video_stream]
        container.streams.audio = [audio_stream]
        container.duration = None
        mock_av_open.return_value.__enter__.return_value = container

        # Test extraction
        metadata = extract_video_metadata("/fake/path/video.mp4")

        self.assertEqual(metadata["width"], 1920)
        self.assertEqual(metadata["height"], 1080)
        self.assertEqual(metadata["frame_rate"], 29.97)
        self.assertEqual(metadata["duration"], 30.0)
        self.assertEqual(metadata["audio_channels"], 2)
        self.assertEqual(metadata["sample_rate"], 48000)
        self.assertEqual(metadata["file_size"], 5242880)

    @patch("cw.lib.video_analysis.metadata.os.path.exists")
    def test_extract_metadata_file_not_found(self, mock_exists):
        """Test error handling for missing video file."""
        from cw.lib.video_analysis import extract_video_metadata

        mock_exists.return_value = False

        with self.assertRaises(FileNotFoundError):
            extract_video_metadata("/fake/path/missing.mp4")

    @patch("cw.lib.video_analysis.metadata.av.open")
    @patch("cw.lib.video_analysis.metadata.os.path.exists")
    @patch("cw.lib.video_analysis.metadata.os.path.getsize")
    def test_extract_metadata_with_container_duration(
        self, mock_getsize, mock_exists, mock_av_open
    ):
        """Test metadata extraction when stream duration is unavailable."""
        from cw.lib.video_analysis import extract_video_metadata

        mock_exists.return_value = True
        mock_getsize.return_value = 1048576

        # Video stream with no duration
        video_stream = Mock()
        video_stream.width = 1280
        video_stream.height = 720
        video_stream.average_rate = 24.0
        video_stream.duration = None

        # Container has duration in microseconds
        container = MagicMock()
        container.streams.video = [video_stream]
        container.streams.audio = []
        container.duration = 15_000_000  # 15 seconds in microseconds
        mock_av_open.return_value.__enter__.return_value = container

        metadata = extract_video_metadata("/fake/path/video.mp4")

        self.assertEqual(metadata["duration"], 15.0)
        self.assertEqual(metadata["width"], 1280)
        self.assertEqual(metadata["height"], 720)


class SceneDetectionTestCase(TestCase):
    """Test detect_scenes utility."""

    @patch("cw.lib.video_analysis.scene_detection.SceneManager")
    @patch("cw.lib.video_analysis.scene_detection.open_video")
    def test_detect_scenes_success(self, mock_open_video, mock_scene_manager_class):
        """Test successful scene detection."""
        from cw.lib.video_analysis import detect_scenes

        # Mock video
        mock_video = Mock()
        mock_open_video.return_value = mock_video

        # Mock FrameTimecode objects
        def create_timecode(seconds, frames):
            tc = Mock()
            tc.get_seconds.return_value = seconds
            tc.get_frames.return_value = frames
            tc.__sub__ = lambda self, other: create_timecode(
                seconds - other.get_seconds(), frames - other.get_frames()
            )
            return tc

        # Mock scene list (3 scenes)
        scene_list = [
            (create_timecode(0.0, 0), create_timecode(3.5, 105)),
            (create_timecode(3.5, 105), create_timecode(8.2, 246)),
            (create_timecode(8.2, 246), create_timecode(15.0, 450)),
        ]

        # Mock scene manager
        mock_scene_manager = Mock()
        mock_scene_manager.get_scene_list.return_value = scene_list
        mock_scene_manager_class.return_value = mock_scene_manager

        # Test detection
        scenes = detect_scenes("/fake/path/video.mp4")

        self.assertEqual(len(scenes), 3)

        # Verify first scene
        self.assertEqual(scenes[0]["scene_number"], 1)
        self.assertEqual(scenes[0]["start_time"], 0.0)
        self.assertEqual(scenes[0]["end_time"], 3.5)
        self.assertEqual(scenes[0]["duration"], 3.5)
        self.assertEqual(scenes[0]["start_frame"], 0)
        self.assertEqual(scenes[0]["end_frame"], 105)

        # Verify last scene
        self.assertEqual(scenes[2]["scene_number"], 3)
        self.assertEqual(scenes[2]["start_time"], 8.2)
        self.assertEqual(scenes[2]["end_time"], 15.0)

    @patch("cw.lib.video_analysis.scene_detection.SceneManager")
    @patch("cw.lib.video_analysis.scene_detection.open_video")
    def test_detect_scenes_with_custom_threshold(
        self, mock_open_video, mock_scene_manager_class
    ):
        """Test scene detection with custom threshold parameter."""
        from cw.lib.video_analysis import detect_scenes

        mock_video = Mock()
        mock_open_video.return_value = mock_video

        mock_scene_manager = Mock()
        mock_scene_manager.get_scene_list.return_value = []
        mock_scene_manager_class.return_value = mock_scene_manager

        # Test with custom threshold
        detect_scenes("/fake/path/video.mp4", threshold=35.0, min_scene_len=30)

        # Verify ContentDetector was created with custom params
        mock_scene_manager.add_detector.assert_called_once()


class AudioTranscriptionTestCase(TestCase):
    """Test transcribe_audio utility."""

    @patch("cw.lib.video_analysis.transcription.whisper.load_model")
    @patch("cw.lib.video_analysis.transcription.torch")
    def test_transcribe_audio_success(self, mock_torch, mock_load_model):
        """Test successful audio transcription."""
        from cw.lib.video_analysis import transcribe_audio

        # Mock device detection
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = True

        # Mock Whisper model
        mock_model = Mock()
        mock_model.transcribe.return_value = {
            "language": "en",
            "segments": [
                {
                    "start": 0.5,
                    "end": 3.2,
                    "text": " Test transcription segment one.",
                    "avg_logprob": -0.15,
                },
                {
                    "start": 3.5,
                    "end": 7.8,
                    "text": " Test transcription segment two.",
                    "avg_logprob": -0.12,
                },
            ],
        }
        mock_load_model.return_value = mock_model

        # Test transcription
        result = transcribe_audio("/fake/path/audio.mp3")

        self.assertEqual(result["language"], "en")
        self.assertEqual(len(result["segments"]), 2)

        # Verify first segment
        self.assertEqual(result["segments"][0]["start"], 0.5)
        self.assertEqual(result["segments"][0]["end"], 3.2)
        self.assertEqual(result["segments"][0]["text"], "Test transcription segment one.")
        self.assertEqual(result["segments"][0]["speaker"], "narrator")
        self.assertGreater(result["segments"][0]["confidence"], 0.8)

        # Verify overall confidence was calculated
        self.assertIn("confidence", result)
        self.assertGreater(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)

    @patch("cw.lib.video_analysis.transcription.whisper.load_model")
    @patch("cw.lib.video_analysis.transcription.torch")
    def test_transcribe_audio_device_selection(self, mock_torch, mock_load_model):
        """Test device selection logic (CUDA > MPS > CPU)."""
        from cw.lib.video_analysis import transcribe_audio

        # Test CUDA path
        mock_torch.cuda.is_available.return_value = True
        mock_torch.backends.mps.is_available.return_value = False

        mock_model = Mock()
        mock_model.transcribe.return_value = {
            "language": "en",
            "segments": [],
        }
        mock_load_model.return_value = mock_model

        transcribe_audio("/fake/path/audio.mp3")

        # Verify model loaded with CUDA
        mock_load_model.assert_called_with("large-v3", device="cuda")

    @patch("cw.lib.video_analysis.transcription.whisper.load_model")
    @patch("cw.lib.video_analysis.transcription.torch")
    def test_transcribe_audio_with_language(self, mock_torch, mock_load_model):
        """Test transcription with specified language."""
        from cw.lib.video_analysis import transcribe_audio

        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = False

        mock_model = Mock()
        mock_model.transcribe.return_value = {
            "language": "es",
            "segments": [],
        }
        mock_load_model.return_value = mock_model

        transcribe_audio("/fake/path/audio.mp3", language="es")

        # Verify transcribe called with language parameter
        call_args = mock_model.transcribe.call_args
        self.assertEqual(call_args[1]["language"], "es")

    @patch("cw.lib.video_analysis.transcription.whisper.load_model")
    @patch("cw.lib.video_analysis.transcription.torch")
    def test_transcribe_audio_confidence_calculation(self, mock_torch, mock_load_model):
        """Test confidence score calculation from log probabilities."""
        from cw.lib.video_analysis import transcribe_audio

        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = False

        # Mock segments with different log probabilities
        mock_model = Mock()
        mock_model.transcribe.return_value = {
            "language": "en",
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "High confidence", "avg_logprob": -0.1},
                {"start": 1.0, "end": 2.0, "text": "Low confidence", "avg_logprob": -0.9},
            ],
        }
        mock_load_model.return_value = mock_model

        result = transcribe_audio("/fake/path/audio.mp3")

        # First segment should have higher confidence than second
        self.assertGreater(
            result["segments"][0]["confidence"], result["segments"][1]["confidence"]
        )

        # Overall confidence should be average
        expected_avg = (0.9 + 0.1) / 2  # (1.0 + -0.1) and (1.0 + -0.9)
        self.assertAlmostEqual(result["confidence"], expected_avg, places=2)
