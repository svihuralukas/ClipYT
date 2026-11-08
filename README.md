# ClipYT

**ClipYT** is a simple tool for quickly downloading and trimming YouTube videos. It combines [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [FFmpeg](https://ffmpeg.org/) to make extracting video clips quick and straightforward.

## Features

* Download videos directly from YouTube.
* Pick the clip range with a slider or by typing start/end times (`HH:MM:SS`).
* Live YouTube preview that jumps to the selected start/end.
* Save only the selected portion as video (MP4) or audio only (MP3).
* Choose where to save the file and under what name.
* Powered by yt-dlp and FFmpeg.

## Requirements

Install these and make sure they are available in your system PATH:

* **Python 3.10+** – runs the app.
* **FFmpeg** – cuts, merges and converts the clips ([download](https://ffmpeg.org/download.html)).
* **Node.js** – yt-dlp needs a JavaScript runtime to solve YouTube's checks; without it some videos fail with *"Failed to fetch video information"* ([download](https://nodejs.org/)).

Python packages (`streamlit`, `yt-dlp`, `yt-dlp-ejs`) are listed in `requirements.txt` and installed automatically.

## Installation

Clone the repository:

```bash
git clone https://github.com/svihuralukas/ClipYT.git
cd ClipYT
```

## Usage

On Windows, run `run.bat`. It creates a virtual environment (`.venv`) on first start, installs the Python packages and opens the app in your browser.

Manually (any OS):

```bash
python -m venv .venv
.venv\Scripts\activate        # Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

In the app:

1. Paste a YouTube URL.
2. Select the range with the slider or type the start/end times.
3. Click **Download clip** (MP4) or **Download audio (MP3)** and choose where to save the file.

The app runs locally on your computer – the save dialog opens on the machine running the app.

## Troubleshooting

If a video that plays on YouTube fails to load, update the packages first (YouTube changes often):

```bash
python -m pip install -U -r requirements.txt
```

## How It Works

ClipYT is a [Streamlit](https://streamlit.io/) app that uses these tools behind the scenes:

* **yt-dlp** downloads only the selected part of the video from YouTube.
* **FFmpeg** cuts, merges and converts the downloaded streams.
* **Node.js** with **yt-dlp-ejs** solves YouTube's JavaScript challenges for yt-dlp.

The goal is to simplify the process of downloading and trimming videos into a single workflow.

## License

This project is open-source. See the repository for licensing information.
