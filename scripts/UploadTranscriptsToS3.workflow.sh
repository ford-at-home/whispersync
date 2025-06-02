#!/bin/bash

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

BUCKET_NAME="macbook-transcriptions"

for f in "$@"
do
  if [[ "$f" == *.txt ]]; then
    # Get creation date of the file
    CREATED_DATE=$(stat -f "%SB" -t "%Y-%m-%d" "$f")
    KEY_NAME=$(basename "$f")
    S3_KEY="transcripts/$CREATED_DATE/$KEY_NAME"

    {
      echo "===== $(date '+%Y-%m-%d %H:%M:%S') — BEGIN UPLOAD: $f ====="
      echo "Uploading to s3://$BUCKET_NAME/$S3_KEY"
      aws s3 cp "$f" "s3://$BUCKET_NAME/$S3_KEY"
      echo "===== $(date '+%Y-%m-%d %H:%M:%S') — END UPLOAD ====="
    } >> ~/transcript_upload.log 2>&1
  fi
done

