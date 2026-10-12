#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
archive_dir="$repo_root/assets/third_party/ycb/downloads"
output_root="${YCB_OUTPUT_ROOT:-$repo_root/assets/third_party/ycb/unpacked}"

(
  cd "$archive_dir"
  sha256sum --check SHA256SUMS
)

mkdir -p "$output_root"

for archive in "$archive_dir"/*_google_16k.tgz; do
  object_name="$(basename "$archive" _google_16k.tgz)"
  expected_prefix="$object_name/google_16k/"

  while IFS= read -r member; do
    case "$member" in
      "$expected_prefix"*) ;;
      *) printf 'Unexpected archive member in %s: %s\n' "$archive" "$member" >&2; exit 1 ;;
    esac
    case "/$member/" in
      *"/../"*) printf 'Unsafe archive path in %s: %s\n' "$archive" "$member" >&2; exit 1 ;;
    esac
  done < <(tar -tzf "$archive")

  tar -xzf "$archive" -C "$output_root" \
    "$expected_prefix"textured.obj \
    "$expected_prefix"textured.mtl \
    "$expected_prefix"texture_map.png
done

printf 'Extracted reviewed YCB Google 16k visual meshes into %s\n' "$output_root"
