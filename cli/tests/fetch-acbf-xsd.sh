#!/bin/sh
# Download the pinned ACBF 1.1 schema used to validate published metadata.
# Usage: tests/fetch-acbf-xsd.sh DEST   (then export COMIC_PANEL_ACBF_XSD=DEST)
set -eu
dest=${1:?destination path}
url='https://raw.githubusercontent.com/ACBF-Advanced-Comic-Book-Format/ACBF/e033e004e2897fe20ad09cbd649a8ba1d6b38d09/XML%20Schema/acbf-1.1.xsd'
want=154e997a600143adf205bfcad427ef6e6fa4a6fcfce10cece4d58a0b64c2ac32
curl -sfL -o "$dest" "$url"
got=$( (sha256sum "$dest" 2>/dev/null || shasum -a 256 "$dest") | cut -d' ' -f1)
[ "$got" = "$want" ] || { echo "ACBF schema checksum mismatch: $got" >&2; rm -f "$dest"; exit 1; }
echo "$dest"
