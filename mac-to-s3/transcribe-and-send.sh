#!/bin/bash
#
# Transcribe audio files using Whisper and upload the resulting text
# to Amazon S3.  Designed to be triggered via an Automator workflow on
# macOS.
#
# Ensure paths to ffmpeg, whisper, and aws CLI are available
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Config
TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
TRANSCRIPT_DIR="$HOME/Documents/transcriptions"
LOG_DIR="$TRANSCRIPT_DIR/logs/$TIMESTAMP"
OUTPUT_DIR="$TRANSCRIPT_DIR/output"
WHISPER_BIN="$HOME/.voice-transcriber-env/bin/whisper"
BUCKET_NAME="macbook-transcriptions"

mkdir -p "$LOG_DIR" "$OUTPUT_DIR"

for f in "$@"
do
  if [[ "$f" == *.m4a ]]; then
    echo "Transcribing: $f" >> "$LOG_DIR/transcription_debug.log"

    {
      echo "===== $(date '+%Y-%m-%d %H:%M:%S') — BEGIN TRANSCRIPTION: $f ====="
      "$WHISPER_BIN" "$f" \
        --language en \
        --output_dir "$OUTPUT_DIR" \
        --output_format txt
      echo "===== $(date '+%Y-%m-%d %H:%M:%S') — END TRANSCRIPTION ====="
    } >> "$LOG_DIR/transcription_error.log" 2>&1
  fi
done

# Upload all new .txt files in output directory
for f in "$OUTPUT_DIR"/*.txt
do
  [ -e "$f" ] || continue
  CREATED_DATE=$(stat -f "%SB" -t "%Y-%m-%d" "$f")
  KEY_NAME=$(basename "$f")
  S3_KEY="transcripts/$CREATED_DATE/$KEY_NAME"

  {
    echo "===== $(date '+%Y-%m-%d %H:%M:%S') — BEGIN UPLOAD: $f ====="
    echo "Uploading to s3://$BUCKET_NAME/$S3_KEY"
    aws s3 cp "$f" "s3://$BUCKET_NAME/$S3_KEY"
    echo "===== $(date '+%Y-%m-%d %H:%M:%S') — END UPLOAD ====="
  } >> "$LOG_DIR/upload.log" 2>&1
done
