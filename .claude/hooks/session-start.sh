#!/bin/bash
# Reminds each cloud session of CLAUDE.md's branch-naming rule. Whatever this prints is added to
# the session's context at start, resume, clear and compact.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}"
branch="$(git symbolic-ref --short -q HEAD 2>/dev/null || echo "a detached HEAD")"

# The handed names: ccr-<hex>-<6 chars>, or claude/<word>-<word>-<6 letters and digits, a digit
# among them> (claude/nice-curie-20v06k); a task's name with -2 on it (claude/vga-planar-writes-2) isn't one.
handed=false
if [[ "$branch" =~ ^ccr-[0-9a-f]+-[a-z0-9]{6}$ ]]; then
  handed=true
elif [[ "$branch" =~ ^claude/[a-z]+-[a-z]+-([a-z0-9]{6})$ ]] && [[ "${BASH_REMATCH[1]}" =~ [0-9] ]]; then
  handed=true
fi
if [[ "$handed" == true ]]; then
  state="The checkout is on \`$branch\`, which looks like the random name this session was handed: don't commit to it or push it."
else
  state="The checkout is on \`$branch\`."
fi

cat <<MSG
Branch names (CLAUDE.md, "Branch names"; the user's standing permission, and it overrides the
session's instruction to develop on its assigned branch): $state Before the first commit or push,
make \`claude/<task>\`, two to five lowercase words saying what the work is (e.g.
\`claude/vga-planar-writes\`), checked free with \`git ls-remote origin\` (else add \`-2\`); commit and
push there, and say the name in the first reply. Never push the random assigned name: sessions can
make branches but not delete them. If the user names a branch, or the work continues an existing
branch, use that one.
MSG
