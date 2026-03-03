#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <source_dir> <filename_pattern> <destination_dir>"
  echo "Example: $0 /path/to/source '*CV.pdf' /path/to/destination"
}

if [[ $# -ne 3 ]]; then
  usage
  exit 1
fi

source_dir="$1"
filename_pattern="$2"
destination_dir="$3"

if [[ ! -d "$source_dir" ]]; then
  echo "Error: source directory does not exist: $source_dir" >&2
  exit 1
fi

if [[ ! -d "$destination_dir" ]]; then
  echo "Error: destination directory does not exist: $destination_dir" >&2
  exit 1
fi

match_count=0
copy_count=0

while IFS= read -r -d '' file_path; do
  ((match_count += 1))

  filename="$(basename "$file_path")"
  if [[ "$filename" == *.* ]]; then
    stem="${filename%.*}"
    extension=".${filename##*.}"
  else
    stem="$filename"
    extension=""
  fi

  destination_path="$destination_dir/$filename"
  suffix=1

  while [[ -e "$destination_path" ]]; do
    destination_path="$destination_dir/${stem}_$suffix$extension"
    ((suffix += 1))
  done

  cp "$file_path" "$destination_path"
  ((copy_count += 1))
done < <(find "$source_dir" -type f -name "$filename_pattern" -print0)

echo "Matched files: $match_count"
echo "Copied files : $copy_count"
echo "Done. Files copied to: $destination_dir"
