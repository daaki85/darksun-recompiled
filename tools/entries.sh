#!/bin/sh
# entries.sh seed|save BUILD [MOD]: the entry-point lists a build converged on (misses.txt, the
# addresses runs found no function at; inside.txt, the addresses in the middle of functions the
# helper sends the game to) kept in the repository, under entries/<name>/, so a fresh clone lifts
# the same program without the discovery runs. The name is the build's (ds1, ds2, ct), and for the
# mod's build ds1o-<the first 8 hex digits of the md5 of the mod's DSCLOG.EXE>: the lists depend on
# the helper's release. `seed` copies the lists into the build folder (merged with what is there);
# `save` copies the build folder's lists back, after a convergence (tools/converge.sh).
set -e
cd "$(dirname "$0")/.."
cmd=$1; B=${2:-build/ds1}; MOD=$3
name=$(basename "$B")
if [ "$name" = ds1o ]; then
  [ -n "$MOD" ] || MOD=../daaki85/darksun-obsidian-edition/obsidian-edition
  key=$(md5sum "$MOD/dos/DSCLOG.EXE" | cut -c1-8)
  name="ds1o-$key"
fi
E=entries/$name
case "$cmd" in
  seed)
    [ -d "$E" ] || { echo "no saved entries for $name ($E): the build converges from scratch"; exit 0; }
    mkdir -p "$B"
    for f in misses.txt inside.txt; do
      [ -f "$E/$f" ] || continue
      cat "$E/$f" "$B/$f" 2>/dev/null | awk 'NF && !seen[$1]++' > "$B/$f.new" && mv "$B/$f.new" "$B/$f"
    done
    echo "seeded $B from $E"
    ;;
  save)
    mkdir -p "$E"
    for f in misses.txt inside.txt; do [ -f "$B/$f" ] && cp "$B/$f" "$E/$f"; done
    echo "saved $B's lists to $E (commit them)"
    ;;
  *) echo "usage: tools/entries.sh seed|save BUILD [MOD]"; exit 1;;
esac
