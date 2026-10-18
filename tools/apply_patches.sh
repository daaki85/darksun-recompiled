#!/bin/sh
# Apply this project's changes to the pcrecomp submodule (patches/pcrecomp),
# after `git submodule update`. Each is also a candidate for upstream.
set -e
cd "$(dirname "$0")/../third_party/pcrecomp"
for p in ../../patches/pcrecomp/*.patch; do
    git apply --check "$p" 2>/dev/null && git apply "$p" && echo "applied $(basename "$p")" || echo "already applied or failed: $(basename "$p")"
done
