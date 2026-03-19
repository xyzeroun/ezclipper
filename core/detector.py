"""
TikTok Clipper — AI Highlight Detection
Uses OpenRouter or KIE AI to analyze video transcripts and identify viral moments.
"""
import os
import json
import base64
import subprocess
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Kamu adalah ahli konten viral TikTok. Tugasmu adalah menganalisis transcript video dan menemukan momen-momen paling menarik dan viral.

Aturan:
1. Pilih 3-5 momen paling menarik dari video
2. Setiap momen harus berdurasi minimal 15 detik dan maksimal 60 detik
3. Pilih momen yang: lucu, kontroversial, mengejutkan, emosional, informatif, atau memiliki "hook" kuat
4. Pastikan setiap clip memiliki awal dan akhir yang natural (tidak terpotong di tengah kalimat)
5. Berikan judul pendek untuk setiap clip

PENTING: Response harus dalam format JSON SAJA, tanpa teks lain:
{
  "clips": [
    {
      "start": 30.5,
      "end": 65.2,
      "title": "Judul pendek clip ini",
      "reason": "Alasan kenapa momen ini menarik"
    }
  ]
}"""


class Detector:
    """AI-powered highlight detection using OpenRouter or KIE AI."""

    def __init__(
        self,
        openrouter_api_key: str = "",
        openrouter_model: str = "openai/gpt-4o-mini",
        kie_api_key: str = "",
        min_clip_duration: int = 15,
        max_clip_duration: int = 60,
        max_clips: int = 5,
    ):
        self.openrouter_api_key = openrouter_api_key
        self.openrouter_model = openrouter_model
        self.kie_api_key = kie_api_key
        self.min_clip_duration = min_clip_duration
        self.max_clip_duration = max_clip_duration
        self.max_clips = max_clips

    def extract_keyframes(self, video_path: str, interval: int = 30, max_frames: int = 10) -> list[str]:
        """
        Extract keyframes from video at regular intervals.
        Returns list of base64-encoded JPEG images.
        """
        duration = self._get_duration(video_path)
        if duration <= 0:
            return []

        # Calculate timestamps for keyframes
        num_frames = min(max_frames, max(1, int(duration / interval)))
        timestamps = [i * (duration / num_frames) for i in range(num_frames)]

        frames = []
        for ts in timestamps:
            frame_path = os.path.join(
                os.path.dirname(video_path),
                f"_keyframe_{ts:.0f}.jpg"
            )
            cmd = [
                "ffmpeg", "-ss", str(ts),
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "5",
                "-vf", "scale=480:-1",
                "-y",
                frame_path,
            ]
            subprocess.run(cmd, capture_output=True)

            if os.path.exists(frame_path):
                with open(frame_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                frames.append(b64)
                os.remove(frame_path)

        logger.info(f"Extracted {len(frames)} keyframes")
        return frames

    def _get_duration(self, video_path: str) -> float:
        """Get video duration in seconds."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return float(data.get("format", {}).get("duration", 0))
        return 0

    def detect_highlights(
        self,
        transcript: dict,
        video_path: str,
        progress_callback=None,
    ) -> list[dict]:
        """
        Detect highlight moments using AI.

        Args:
            transcript: output from Transcriber.transcribe()
            video_path: path to video file for keyframe extraction

        Returns list of highlights: [{start, end, title, reason}, ...]
        """
        if progress_callback:
            progress_callback("detect", 10)

        # Extract keyframes for visual context
        keyframes = self.extract_keyframes(video_path)

        if progress_callback:
            progress_callback("detect", 30)

        # Format transcript with timestamps for the AI
        formatted_transcript = self._format_transcript(transcript)

        # Build the prompt
        user_prompt = f"""Berikut adalah transcript video dengan timestamps:

{formatted_transcript}

Durasi video: {transcript.get('duration', 0):.1f} detik

Tolong analisis dan pilih {self.max_clips} momen paling menarik/viral untuk dijadikan clip TikTok.
Setiap clip harus berdurasi {self.min_clip_duration}-{self.max_clip_duration} detik.

Response dalam format JSON saja."""

        if progress_callback:
            progress_callback("detect", 40)

        # Call AI API
        if self.openrouter_api_key:
            result = self._call_openrouter(user_prompt, keyframes)
        elif self.kie_api_key:
            result = self._call_kie(user_prompt, keyframes)
        else:
            raise ValueError("No API key configured. Set OpenRouter or KIE AI API key in settings.")

        if progress_callback:
            progress_callback("detect", 90)

        # Parse and validate
        clips = self._parse_response(result, transcript.get("duration", 0))

        if progress_callback:
            progress_callback("detect", 100)

        logger.info(f"Detected {len(clips)} highlights")
        return clips

    def _format_transcript(self, transcript: dict) -> str:
        """Format transcript segments with timestamps."""
        lines = []
        for seg in transcript.get("segments", []):
            start = self._format_time(seg["start"])
            end = self._format_time(seg["end"])
            lines.append(f"[{start} - {end}] {seg['text']}")
        return "\n".join(lines)

    def _format_time(self, seconds: float) -> str:
        """Format seconds to MM:SS."""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"

    def _call_openrouter(self, prompt: str, keyframes: list[str]) -> str:
        """Call OpenRouter API."""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]

        # Build user message with optional images
        content_parts = []

        # Add keyframes as images (max 5 to manage cost)
        for i, frame_b64 in enumerate(keyframes[:5]):
            content_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{frame_b64}",
                    "detail": "low",
                },
            })

        content_parts.append({
            "type": "text",
            "text": prompt,
        })

        messages.append({"role": "user", "content": content_parts})

        logger.info(f"Calling OpenRouter: {self.openrouter_model}")

        with httpx.Client(timeout=120) as client:
            resp = client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.openrouter_model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 2000,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return data["choices"][0]["message"]["content"]

    def _call_kie(self, prompt: str, keyframes: list[str]) -> str:
        """Call KIE AI API."""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]

        content_parts = []
        for frame_b64 in keyframes[:5]:
            content_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{frame_b64}",
                },
            })

        content_parts.append({
            "type": "text",
            "text": prompt,
        })

        messages.append({"role": "user", "content": content_parts})

        logger.info("Calling KIE AI")

        with httpx.Client(timeout=120) as client:
            resp = client.post(
                "https://api.kie.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.kie_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 2000,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return data["choices"][0]["message"]["content"]

    def _parse_response(self, response_text: str, video_duration: float) -> list[dict]:
        """Parse AI response and validate clip timestamps."""
        # Extract JSON from response
        text = response_text.strip()

        # Try to find JSON block
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in text
            start_idx = text.find("{")
            end_idx = text.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                data = json.loads(text[start_idx:end_idx])
            else:
                logger.error(f"Failed to parse AI response: {text[:500]}")
                raise ValueError("AI response is not valid JSON")

        clips = data.get("clips", [])

        # Validate and clean up
        valid_clips = []
        for clip in clips:
            start = float(clip.get("start", 0))
            end = float(clip.get("end", 0))
            duration = end - start

            # Validate
            if start < 0:
                start = 0
            if end > video_duration:
                end = video_duration
            if duration < self.min_clip_duration:
                end = min(start + self.min_clip_duration, video_duration)
            if duration > self.max_clip_duration:
                end = start + self.max_clip_duration

            if end > start:
                valid_clips.append({
                    "start": round(start, 2),
                    "end": round(end, 2),
                    "title": clip.get("title", f"Clip {len(valid_clips) + 1}"),
                    "reason": clip.get("reason", ""),
                })

        return valid_clips[:self.max_clips]
