
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime, time, timedelta
from urllib.parse import urlparse
import yt_dlp
from yt_dlp.utils import download_range_func

import streamlit as st

APP_DIR = Path(__file__).parent
OUTPUT_DIR = Path.home() / "Downloads"
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

@st.cache_data(show_spinner="Loading video information...")
def get_video_info(url):
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

    return info.get("duration"), info.get("id")

# YouTube player that loads once and only seeks when the range changes.
YT_PREVIEW_JS = """
function loadYouTubeApi() {
    if (!window.__ytApi) {
        window.__ytApi = new Promise((resolve) => {
            if (window.YT && window.YT.Player) {
                resolve(window.YT);
                return;
            }
            const previous = window.onYouTubeIframeAPIReady;
            window.onYouTubeIframeAPIReady = () => {
                if (previous) previous();
                resolve(window.YT);
            };
            const tag = document.createElement("script");
            tag.src = "https://www.youtube.com/iframe_api";
            document.head.appendChild(tag);
        });
    }
    return window.__ytApi;
}

export default function({ parentElement, data }) {
    const root = parentElement.querySelector(".yt-preview");
    const state = root.__state || (root.__state = {});
    const { video_id, start, end } = data;
    state.end = end;

    if (state.videoId !== video_id) {
        state.videoId = video_id;
        state.start = start;
        state.lastEnd = end;
        state.player = null;
        root.innerHTML = "<div></div>";

        loadYouTubeApi().then((YT) => {
            state.player = new YT.Player(root.firstChild, {
                videoId: video_id,
                playerVars: { start: start, rel: 0 },
                events: {
                    // After seeking a not-yet-started video, pause as soon as
                    // the frame is rendered (pausing earlier leaves it black).
                    onStateChange: (event) => {
                        if (event.data === YT.PlayerState.PLAYING && state.pauseOnPlay) {
                            state.pauseOnPlay = false;
                            event.target.pauseVideo();
                            if (!state.wasMuted) event.target.unMute();
                        }
                    },
                },
            });

            // Stop playback at the end of the selected range.
            const timer = setInterval(() => {
                if (!root.isConnected) {
                    clearInterval(timer);
                    return;
                }
                const player = state.player;
                if (
                    player && player.getPlayerState &&
                    player.getPlayerState() === YT.PlayerState.PLAYING &&
                    player.getCurrentTime() >= state.end
                ) {
                    player.pauseVideo();
                }
            }, 250);
        });
        return;
    }

    const player = state.player;
    let target = null;
    if (start !== state.start) target = start;
    else if (end !== state.lastEnd) target = end;
    state.start = start;
    state.lastEnd = end;

    if (target === null || !player || !player.seekTo) return;

    const playerState = player.getPlayerState();
    const { PLAYING, PAUSED, BUFFERING } = window.YT.PlayerState;

    if (playerState !== PLAYING && playerState !== PAUSED && playerState !== BUFFERING) {
        // Seeking an unstarted/cued/ended video starts playback.
        if (!state.pauseOnPlay) state.wasMuted = player.isMuted();
        state.pauseOnPlay = true;
        player.mute();
    }
    player.seekTo(target, true);
}
"""

yt_preview = st.components.v2.component(
    "yt_preview",
    html='<div class="yt-preview"></div>',
    css="""
.yt-preview, .yt-preview iframe {
    width: 100%;
    aspect-ratio: 16 / 9;
    border: 0;
}
""",
    js=YT_PREVIEW_JS,
    isolate_styles=False
)

def to_seconds(value):
    return value.hour * 3600 + value.minute * 60 + value.second

def to_time(value):
    return time(value // 3600, (value % 3600) // 60, value % 60)

if not url:
    st.info("Paste a YouTube URL to load the video.")
    st.stop()

if not valid_youtube_url(url):
    st.error("Enter a valid YouTube URL.")
    st.stop()

try:
    duration, video_id = get_video_info(url)

except subprocess.TimeoutExpired:
    st.error("Loading video information timed out. Please try again.")
    st.stop()

except Exception as e:
    st.error(f"Error during video processing: {e}")
    st.stop()

if duration is None:
    st.error("Failed to fetch video information.")
    st.stop()

duration = int(duration)

range_key = f"range_{url}"
start_key = f"start_{url}"
end_key = f"end_{url}"
error_key = f"time_error_{url}"

def parse_time(value):
    match = re.fullmatch(r"(\d{1,2}):(\d{2}):(\d{2})", value.strip())
    if not match:
        return None
    h, m, s = map(int, match.groups())
    if m >= 60 or s >= 60:
        return None
    return h * 3600 + m * 60 + s

def sync_text_from_slider():
    start_value, end_value = st.session_state[range_key]
    st.session_state[start_key] = start_value.strftime("%H:%M:%S")
    st.session_state[end_key] = end_value.strftime("%H:%M:%S")
    st.session_state[error_key] = None

def sync_slider_from_text():
    start_value = parse_time(st.session_state[start_key])
    end_value = parse_time(st.session_state[end_key])

    if start_value is None or end_value is None:
        error = "Time must be in HH:MM:SS format."
    elif end_value > duration:
        error = (
            f"End time exceeds video length "
            f"({to_time(duration).strftime('%H:%M:%S')})."
        )
    elif start_value > end_value:
        error = "Start time must not be later than end time."
    else:
        st.session_state[range_key] = (to_time(start_value), to_time(end_value))
        st.session_state[error_key] = None
        return

    sync_text_from_slider()
    st.session_state[error_key] = error

if range_key not in st.session_state:
    st.session_state[range_key] = (time(0, 0, 0), to_time(min(60, duration)))
    sync_text_from_slider()

start_time, end_time = st.session_state[range_key]

start = to_seconds(start_time)
end = to_seconds(end_time)

if video_id:
    yt_preview(
        data={"video_id": video_id, "start": start, "end": end},
        key=f"preview_{url}"
    )

st.slider(
    "Clip range",
    min_value=time(0, 0, 0),
    max_value=to_time(duration),
    step=timedelta(seconds=1),
    format="HH:mm:ss",
    key=range_key,
    on_change=sync_text_from_slider
)

col1, col2 = st.columns(2)

with col1:
    st.text_input("Start (HH:MM:SS)", key=start_key, on_change=sync_slider_from_text)

with col2:
    st.text_input("End (HH:MM:SS)", key=end_key, on_change=sync_slider_from_text)

if st.session_state.get(error_key):
    st.warning(st.session_state[error_key])

st.caption(
    f"Clip length: {to_time(max(end - start, 0)).strftime('%H:%M:%S')}"
)

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

if st.button("Download clip", type="primary", use_container_width=True):

    if end <= start:
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
            [(start, end)]
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

        st.success("File was successfully created and saved!")

        st.info(f"Saved to: `{video_path.resolve()}`")

        if expected_extension == ".mp3":
            st.audio(str(video_path))
        else:
            st.video(str(video_path))

        st.write(
            f"Size: {video_path.stat().st_size / 1024 / 1024:.2f} MB"
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