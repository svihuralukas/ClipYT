
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import yt_dlp
from yt_dlp.utils import download_range_func

import streamlit as st

APP_DIR = Path(__file__).parent
OUTPUT_DIR = APP_DIR / "clips"
OUTPUT_DIR.mkdir(exist_ok=True)

st.set_page_config(
    page_title="ClipYT",
    layout="centered"
)

st.title("ClipYT")
st.caption("YouTube Video Clipper · Local version")

st.divider()

url = st.text_input(
    "YouTube URL",
    placeholder="https://www.youtube.com/watch?v=..."
)

col1, col2 = st.columns(2)

with col1:
    start = st.text_input("Start (HH:MM:SS)", "00:00:00")

with col2:
    end = st.text_input("End (HH:MM:SS)", "00:01:00")

quality = st.selectbox(
    "Output quality",
    [
        "Best available",
        "720",
        "1080",
        "1440",
        "2160"
    ],
    index=0,
    format_func=lambda x: (
        "Best available (maximum)"
        if x == "Best available"
        else f"{x}p"
    )
)

output_format = st.selectbox(
    "Output format",
    ["MP4 (Video)", "MP3 (Audio)"]
)

def valid_time(value):
    return bool(re.fullmatch(r"\d{2,}:\d{2}:\d{2}", value))

def seconds(value):
    h, m, s = map(int, value.split(":"))
    return h * 3600 + m * 60 + s

def valid_youtube_url(value):
    try:
        host = urlparse(value).hostname or ""
        return host.lower() in {
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
            "youtu.be",
            "www.youtu.be"
        }
    except Exception:
        return False

def get_video_duration(url):
    command = [
        sys.executable,
        "-m", "yt_dlp",
        "--dump-single-json",
        "--no-playlist",
        "--skip-download",
        url
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=60
    )

    if result.returncode != 0:
        raise Exception("Failed to fetch video information.")

    import json
    info = json.loads(result.stdout)

    return info.get("duration")

try:
    duration = get_video_duration(url)

    if duration is None:
        st.error("Failed to fetch video information.")
        st.stop()

    if seconds(end) > duration:
        st.error(
            f"End time ({end}) exceeds "
            f"video length ({duration // 3600:02d}:"
            f"{(duration % 3600) // 60:02d}:"
            f"{duration % 60:02d})."
        )
        st.stop()

except subprocess.TimeoutExpired:
    st.error("Loading video information timed out. Please try again.")
    st.stop()

except Exception as e:
    st.error(f"Error during video processing: {e}")
    st.stop()


if st.button("Download clip", type="primary", use_container_width=True):

    if not valid_youtube_url(url):
        st.error("Enter a valid YouTube URL.")
        st.stop()

    if not valid_time(start) or not valid_time(end):
        st.error("Time must be in HH:MM:SS format.")
        st.stop()

    if seconds(end) <= seconds(start):
        st.error("End time must be later than start time.")
        st.stop()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_template = str(
        OUTPUT_DIR / f"clip_{timestamp}.%(ext)s"
    )

    if output_format == "MP3 (Audio)":
        expected_extension = ".mp3"
    else:
        expected_extension = ".mp4"

    # Progress UI
    st.subheader("Download progress")

    video_progress = st.empty()
    audio_progress = st.empty()
    combined_progress = st.empty()
    status_text = st.empty()

    progress_values = {
        "video": 0,
        "audio": 0,
        "combined": 0
    }

    def progress_hook(data):
        if data["status"] == "downloading":
            info = data.get("info_dict", {})

            vcodec = info.get("vcodec")
            acodec = info.get("acodec")

            has_video = vcodec and vcodec != "none"
            has_audio = acodec and acodec != "none"

            if has_video and not has_audio:
                stream_type = "video"
                label = "Video"
            elif has_audio and not has_video:
                stream_type = "audio"
                label = "Audio"
            else:
                stream_type = "combined"
                label = "Video + audio"

            downloaded = data.get("downloaded_bytes", 0)
            total = (
                data.get("total_bytes")
                or data.get("total_bytes_estimate")
            )

            if total:
                percent = min(
                    int(downloaded / total * 100),
                    100
                )

                progress_values[stream_type] = percent

                size_mb = downloaded / 1024 / 1024
                total_mb = total / 1024 / 1024

                text = (
                    f"{label}: {percent}% "
                    f"({size_mb:.1f} / {total_mb:.1f} MB)"
                )

                if stream_type == "video":
                    video_progress.progress(percent, text=text)

                elif stream_type == "audio":
                    audio_progress.progress(percent, text=text)

                else:
                    combined_progress.progress(percent, text=text)

            status_text.info(f"Downloading: {label}...")

        elif data["status"] == "finished":
            info = data.get("info_dict", {})

            vcodec = info.get("vcodec")
            acodec = info.get("acodec")

            has_video = vcodec and vcodec != "none"
            has_audio = acodec and acodec != "none"

            if has_video and not has_audio:
                stream_type = "video"
                label = "Video"
                placeholder = video_progress
            elif has_audio and not has_video:
                stream_type = "audio"
                label = "Audio"
                placeholder = audio_progress
            else:
                stream_type = "combined"
                label = "Video + audio"
                placeholder = combined_progress

            progress_values[stream_type] = 100
            placeholder.progress(100, text=f"{label}: 100%")

    def postprocessor_hook(data):
        status = data.get("status")

        if status == "started":
            status_text.info("Processing video with FFmpeg...")

        elif status == "finished":
            status_text.info("Processing completed.")

    # yt-dlp settings
    ydl_options = {
        "outtmpl": output_template,
        "noplaylist": True,
        "overwrites": True,
        "download_ranges": download_range_func(
            None,
            [(seconds(start), seconds(end))]
        ),
        "progress_hooks": [progress_hook],
        "postprocessor_hooks": [postprocessor_hook],
        "quiet": True,
        "no_warnings": True,
    }

    if output_format == "MP3 (Audio)":

        ydl_options.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "0",
            }]
        })

    else:

        ydl_options.update({
            "format": (
                "bv*+ba/b"
                if quality == "Best available"
                else f"bv*[height<={quality}]+ba/b[height<={quality}]"
            ),
            "merge_output_format": "mp4",
            "force_keyframes_at_cuts": True,
        })

    try:
        status_text.info("Preparing download...")

        with yt_dlp.YoutubeDL(ydl_options) as ydl:
            ydl.extract_info(url, download=True)

        video_path = OUTPUT_DIR / f"clip_{timestamp}{expected_extension}"

        if not video_path.exists():
            st.error("Resulting file not found.")
            st.stop()

        status_text.success("Download completed!")

        st.success("Súbor bol úspešne vytvorený a uložený!")

        st.info(f"📁 Uložené do: `{video_path.resolve()}`")

        if expected_extension == ".mp3":
            st.audio(str(video_path))
        else:
            st.video(str(video_path))

        st.write(
            f"Veľkosť: {video_path.stat().st_size / 1024 / 1024:.2f} MB"
        )

        # file_bytes = video_path.read_bytes()

        # mime_type = (
        #     "audio/mpeg"
        #     if expected_extension == ".mp3"
        #     else "video/mp4"
        # )

        # st.download_button(
        #     "Download",
        #     data=file_bytes,
        #     file_name=video_path.name,
        #     mime=mime_type,
        #     use_container_width=True
        # )

    except Exception as e:
        status_text.error("Downloading or processing failed.")
        st.exception(e)

st.divider()

st.caption("ClipYT · Personal video clipping tool")
st.caption("Download only videos you own or have permission to copy.")