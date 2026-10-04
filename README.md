# ClipYT

**ClipYT** is a simple tool for quickly downloading and trimming YouTube videos. It combines [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [FFmpeg](https://ffmpeg.org/) to make extracting video clips quick and straightforward.

## Features

* Download videos directly from YouTube.
* Trim videos by specifying start and end timestamps.
* Save only the selected portion of a video.
* Simple workflow without manually combining multiple commands.
* Powered by yt-dlp and FFmpeg.

## Requirements

Make sure the following tools are installed and available in your system PATH:

* **yt-dlp** – for downloading YouTube videos.
* **FFmpeg** – for video processing and trimming.

## Installation

Clone the repository:

```bash
git clone https://github.com/svihuralukas/ClipYT.git
cd ClipYT
```

Install the required dependencies (if not already installed):

* [yt-dlp installation guide](https://github.com/yt-dlp/yt-dlp#installation)
* [FFmpeg download](https://ffmpeg.org/download.html)

## Usage

Use ClipYT to download a YouTube video and extract the desired section.

*Usage instructions depend on the selected entry point and interface.*

## How It Works

ClipYT uses two tools behind the scenes:

* **yt-dlp** handles downloading video content from YouTube.
* **FFmpeg** processes the downloaded video and extracts the requested segment.

The goal is to simplify the process of downloading and trimming videos into a single workflow.

## License

This project is open-source. See the repository for licensing information.
