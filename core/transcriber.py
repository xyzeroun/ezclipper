"""
TikTok Clipper — Audio Transcription
Uses faster-whisper for local, free transcription with word-level timestamps.
"""
import os
import subprocess
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class Transcriber:
    """Transcribe video audio using faster-whisper with word-level timestamps."""

    def __init__(self, model_size: str = "base", language: str = "id"):
        """
        Args:
            model_size: Whisper model size (tiny, base, small, medium, large-v3)
            language: Language code for transcription
        """
        self.model_size = model_size
        self.language = language
        self._model = None

    def _load_model(self):
        """Lazy-load the whisper model."""
        if self._model is None:
            logger.info(f"Loading whisper model: {self.model_size}")
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8",
            )
            logger.info("Whisper model loaded")

    def extract_audio(self, video_path: str, output_path: Optional[str] = None) -> str:
        """Extract audio from video using FFmpeg."""
        if output_path is None:
            base = os.path.splitext(video_path)[0]
            output_path = f"{base}_audio.wav"

        if os.path.exists(output_path):
            os.remove(output_path)

        cmd = [
            "ffmpeg", "-i", video_path,
            "-vn",                      # no video
            "-acodec", "pcm_s16le",     # WAV format
            "-ar", "16000",             # 16kHz sample rate (optimal for whisper)
            "-ac", "1",                 # mono
            "-y",                       # overwrite
            output_path,
        ]

        logger.info(f"Extracting audio: {video_path} -> {output_path}")
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg audio extraction failed: {result.stderr}")

        return output_path

    def transcribe(self, video_path: str, progress_callback=None) -> dict:
        """
        Transcribe a video file.

        Returns dict with:
            - text: full transcript text
            - segments: list of segments with timestamps
            - words: list of words with precise timestamps
                     [{word, start, end}, ...]
        """
        self._load_model()

        # Extract audio first
        if progress_callback:
            progress_callback("transcribe", 5)

        audio_path = self.extract_audio(video_path)

        if progress_callback:
            progress_callback("transcribe", 15)

        logger.info(f"Transcribing: {audio_path}")

        segments_gen, info = self._model.transcribe(
            audio_path,
            language=self.language,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500,
            ),
        )

        full_text = []
        segments = []
        all_words = []

        segment_list = list(segments_gen)
        total_segments = len(segment_list) if segment_list else 1

        for i, segment in enumerate(segment_list):
            full_text.append(segment.text.strip())
            seg_data = {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "words": [],
            }

            if segment.words:
                for w in segment.words:
                    word_data = {
                        "word": w.word.strip(),
                        "start": w.start,
                        "end": w.end,
                    }
                    seg_data["words"].append(word_data)
                    all_words.append(word_data)

            segments.append(seg_data)

            if progress_callback:
                pct = 15 + (80 * (i + 1) / total_segments)
                progress_callback("transcribe", min(pct, 95))

        # Clean up audio file
        try:
            os.remove(audio_path)
        except OSError:
            pass

        if progress_callback:
            progress_callback("transcribe", 100)

        result = {
            "text": " ".join(full_text),
            "segments": segments,
            "words": all_words,
            "language": info.language,
            "duration": info.duration,
        }

        logger.info(
            f"Transcription complete: {len(all_words)} words, "
            f"{len(segments)} segments, {info.duration:.1f}s"
        )

        return result
