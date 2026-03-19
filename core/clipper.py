"""
TikTok Clipper — Video Clipper & Caption Generator
Uses FFmpeg for clipping, reframing (landscape → portrait), and burning
TikTok-style word-by-word highlight captions.
"""
import os
import subprocess
import logging
import math
from typing import Optional

logger = logging.getLogger(__name__)


class Clipper:
    """Clip, reframe, and add captions to video segments using FFmpeg."""

    def __init__(
        self,
        output_dir: str,
        resolution: str = "720p",
        fps: int = 30,
        caption_font_size: int = 20,
        caption_color: str = "#FFFFFF",
        caption_highlight_color: str = "#FFD700",
        caption_position: str = "bottom",
    ):
        self.output_dir = output_dir
        self.resolution = resolution
        self.fps = fps
        self.caption_font_size = caption_font_size
        self.caption_color = caption_color
        self.caption_highlight_color = caption_highlight_color
        self.caption_position = caption_position
        os.makedirs(output_dir, exist_ok=True)

    def _get_resolution_values(self) -> tuple[int, int]:
        """Get width x height for portrait (9:16) output."""
        res_map = {
            "480p": (270, 480),
            "720p": (406, 720),     # 9:16 at 720p height
            "1080p": (608, 1080),
        }
        return res_map.get(self.resolution, (406, 720))

    def create_clip(
        self,
        video_path: str,
        start: float,
        end: float,
        words: list[dict],
        clip_index: int = 1,
        title: str = "clip",
        progress_callback=None,
    ) -> str:
        """
        Create a single clip with reframing and captions.

        Args:
            video_path: source video file
            start: start time in seconds
            end: end time in seconds
            words: word-level timestamps from transcriber [{word, start, end}, ...]
            clip_index: clip number for filename
            title: clip title for filename

        Returns: path to output clip file
        """
        safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()[:40]
        output_file = os.path.join(
            self.output_dir,
            f"clip_{clip_index:02d}_{safe_title}.mp4"
        )

        if progress_callback:
            progress_callback("clip", clip_index * 10)

        # Step 1: Generate ASS subtitle file
        ass_path = os.path.join(
            self.output_dir,
            f"_temp_caption_{clip_index}.ass"
        )
        clip_words = self._get_words_in_range(words, start, end)
        self._generate_ass_captions(clip_words, start, ass_path)

        # Step 2: Build FFmpeg command
        width, height = self._get_resolution_values()

        # Escape paths for FFmpeg filter (Windows backslashes)
        ass_path_escaped = ass_path.replace("\\", "/").replace(":", "\\:")

        # Complex filter: crop to center portrait + burn ASS subtitles
        filter_complex = (
            f"[0:v]crop=ih*9/16:ih:(iw-ih*9/16)/2:0,"
            f"scale={width}:{height},"
            f"setsar=1,"
            f"ass='{ass_path_escaped}'[outv]"
        )

        cmd = [
            "ffmpeg",
            "-ss", str(start),
            "-to", str(end),
            "-i", video_path,
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-r", str(self.fps),
            "-movflags", "+faststart",
            "-y",
            output_file,
        ]

        logger.info(f"Creating clip {clip_index}: {start:.1f}s - {end:.1f}s -> {output_file}")
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )

        # If crop filter fails (video already portrait), try without crop
        if result.returncode != 0:
            logger.warning("Crop filter failed, trying direct scale...")
            filter_complex = (
                f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,"
                f"setsar=1,"
                f"ass='{ass_path_escaped}'[outv]"
            )
            cmd[cmd.index("-filter_complex") + 1] = filter_complex
            result = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
            )

        # Clean up ASS file
        try:
            os.remove(ass_path)
        except OSError:
            pass

        if result.returncode != 0:
            logger.error(f"FFmpeg failed: {result.stderr[-500:]}")
            raise RuntimeError(f"FFmpeg clip creation failed: {result.stderr[-200:]}")

        logger.info(f"Clip created: {output_file}")
        return output_file

    def create_all_clips(
        self,
        video_path: str,
        highlights: list[dict],
        words: list[dict],
        progress_callback=None,
    ) -> list[dict]:
        """
        Create all clips from detected highlights.

        Returns list of dicts: [{file_path, title, start, end, duration}, ...]
        """
        results = []
        total = len(highlights)

        for i, highlight in enumerate(highlights):
            if progress_callback:
                pct = (i / total) * 100
                progress_callback("clip", pct)

            try:
                output_file = self.create_clip(
                    video_path=video_path,
                    start=highlight["start"],
                    end=highlight["end"],
                    words=words,
                    clip_index=i + 1,
                    title=highlight.get("title", f"clip_{i+1}"),
                )
                results.append({
                    "file_path": output_file,
                    "title": highlight.get("title", f"Clip {i+1}"),
                    "reason": highlight.get("reason", ""),
                    "start": highlight["start"],
                    "end": highlight["end"],
                    "duration": highlight["end"] - highlight["start"],
                })
            except Exception as e:
                logger.error(f"Failed to create clip {i+1}: {e}")
                results.append({
                    "file_path": None,
                    "title": highlight.get("title", f"Clip {i+1}"),
                    "error": str(e),
                    "start": highlight["start"],
                    "end": highlight["end"],
                })

        if progress_callback:
            progress_callback("clip", 100)

        return results

    def _get_words_in_range(self, words: list[dict], start: float, end: float) -> list[dict]:
        """Filter words that fall within the clip time range."""
        return [
            {
                "word": w["word"],
                "start": w["start"] - start,  # Adjust to clip-relative time
                "end": w["end"] - start,
            }
            for w in words
            if w["start"] >= start and w["end"] <= end
        ]

    def _generate_ass_captions(self, words: list[dict], clip_offset: float, output_path: str):
        """
        Generate ASS subtitle file with TikTok-style word-by-word highlighting.
        Each line shows ~4-6 words, with the current word highlighted.
        """
        width, height = self._get_resolution_values()
        font_size = self.caption_font_size

        # ASS color format: &HBBGGRR& (reversed from RGB, no alpha)
        primary_color = self._hex_to_ass_color(self.caption_color)
        highlight_color = self._hex_to_ass_color(self.caption_highlight_color)

        # Y position for captions
        if self.caption_position == "center":
            margin_v = height // 2 - 20
        else:  # bottom
            margin_v = 40

        header = f"""[Script Info]
Title: TikTok Captions
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{font_size},{primary_color},&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,2,10,10,{margin_v},1
Style: Highlight,Arial,{font_size},{highlight_color},&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,2,10,10,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        events = []

        # Group words into lines of 4-6 words
        words_per_line = 5
        lines = []
        for i in range(0, len(words), words_per_line):
            group = words[i:i + words_per_line]
            if group:
                lines.append(group)

        for line_words in lines:
            if not line_words:
                continue

            line_start = line_words[0]["start"]
            line_end = line_words[-1]["end"]

            # For each word in the line, create highlighting
            for j, word in enumerate(line_words):
                word_start = word["start"]
                word_end = word["end"]

                # Build the line text with the current word highlighted
                parts = []
                for k, w in enumerate(line_words):
                    if k == j:
                        # Highlighted word
                        parts.append(
                            "{\\c" + highlight_color + "\\b1}"
                            + w["word"]
                            + "{\\c" + primary_color + "\\b0}"
                        )
                    else:
                        parts.append(w["word"])

                text = " ".join(parts)

                start_ts = self._seconds_to_ass_time(max(0, word_start))
                end_ts = self._seconds_to_ass_time(word_end)

                events.append(
                    f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{text}"
                )

        ass_content = header + "\n".join(events) + "\n"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ass_content)

        logger.debug(f"ASS captions written: {output_path} ({len(events)} events)")

    def _hex_to_ass_color(self, hex_color: str) -> str:
        """Convert #RRGGBB to ASS &HBBGGRR& format."""
        hex_color = hex_color.lstrip("#")
        r = hex_color[0:2]
        g = hex_color[2:4]
        b = hex_color[4:6]
        return f"&H00{b}{g}{r}&"

    def _seconds_to_ass_time(self, seconds: float) -> str:
        """Convert seconds to ASS timestamp format H:MM:SS.CC."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centis = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"
