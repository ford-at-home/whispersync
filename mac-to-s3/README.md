# Voice Memo Transcription Pipeline (macOS)

This folder contains a fully automated pipeline for transcribing voice memos recorded on your iPhone or Mac, storing the outputs, and syncing them to the cloud.

## What It Does

When you drop `.m4a` files (like voice memos) onto the appropriate folder or run the associated Automator workflow, this system:

1. **Transcribes** the audio using [Whisper](https://github.com/openai/whisper)
2. **Stores** the plain-text transcripts in `~/Documents/transcriptions/output`
3. **Logs** each run into a **timestamped log folder** inside `~/Documents/transcriptions/logs/`
4. **Uploads** the `.txt` files to your designated S3 bucket under a date-organized path

There’s also a symlinked `Recordings/` folder in here that points directly to your system's internal Voice Memos folder for quick access.

## Why This Exists

This system was built to remove friction from the process of capturing and revisiting voice memos. Whether you’re journaling, capturing podcast ideas, or dictating drafts, this setup turns raw audio into searchable, timestamped transcripts — automatically.

By linking to your Apple Voice Memos folder and centralizing outputs and logs in one place, the workflow becomes clean, inspectable, and extensible.

## Setup Details

- Logs are written per run to `logs/YYYY-MM-DD_HH-MM-SS/`
- Transcripts go to `output/`
- Original recordings can be accessed via `Recordings/` (symlink to Apple's internal folder)
- All `.log` files are set to open in Atom for quick review
- Transcripts are uploaded to `s3://macbook-transcriptions/transcripts/{date}/{filename}.txt`

## Want to Build Something Similar?

Check out the blog post that inspired this setup:  
👉 [Automating Voice Memo Transcription](https://fordprior.com/2025/06/02/automating-voice-memo-transcription/)

---
Built by [Ford Prior](https://fordprior.com) · 2025
