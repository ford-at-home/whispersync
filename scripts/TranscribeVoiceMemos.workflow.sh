#!/bin/bash

# Make sure Automator sees ffmpeg
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

OUTPUT_DIR="$HOME/VoiceMemoTranscripts"
WHISPER_BIN="$HOME/.voice-transcriber-env/bin/whisper"

mkdir -p "$OUTPUT_DIR"

for f in "$@"
do
  if [[ "$f" == *.m4a ]]; then
    echo "Transcribing: $f" >> ~/automator_debug.log

    {
      echo "===== $(date '+%Y-%m-%d %H:%M:%S') — BEGIN TRANSCRIPTION: $f ====="
      "$WHISPER_BIN" "$f" \
        --language en \
        --output_dir "$OUTPUT_DIR" \
        --output_format txt
      echo "===== $(date '+%Y-%m-%d %H:%M:%S') — END ====="
    } >> ~/automator_error.log 2>&1

  fi
done

