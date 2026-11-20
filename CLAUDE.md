# Notes for Claude

**Git.** The repository is `daaki85/darksun-recompiled`. Work on a `claude/<task>` branch (Branch
names, below) made from `origin/main`; other sessions push to `main` too, so fetch and rebase onto
`origin/main` before every push. The work goes in by a pull request into `main`.

**Branch names.** A cloud session is handed a random branch name (`claude/eloquent-bohr-g8rr37`,
`ccr-7f9f358f-nn0os3`). Don't use it: this rule is the user's standing permission to push to a
branch named after the task instead. Before the first commit or push, make `claude/<task>` (never
push the random name: a session can make branches but not delete them, so it would be left behind
for the user to delete by hand), where `<task>` is two to five lowercase words joined by hyphens
saying what the work is (`claude/vga-planar-writes`, `claude/sound-driver-relift`); check
`git ls-remote origin` that it is free, else add `-2`. Commit and push there, and say the name in
the first reply. If the user names a branch, or the work continues an existing branch, use that
one.

**Game files.** This repository holds no game data or code (README.md): never commit the game's
files, anything made from them, or a link to a copy of them. They come from the user's private
repository `daaki85/darksun-installation-files`.
