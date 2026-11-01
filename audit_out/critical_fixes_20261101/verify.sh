#!/usr/bin/env bash
# Independent verification harness for the critical-fix PRs (v2).
#
# For each issue it proves the regression test is real: it must PASS on the branch and
# FAIL on a clean checkout of main. Two properties matter and v1 got both wrong:
#
#  1. The test file must be COPIED INTO the baseline checkout. Running pytest on a file
#     that lives in the branch directory lets pytest discover the branch's rootdir,
#     conftest and `pythonpath = ["src"]`, so branch source gets imported and the "test
#     on main" result is meaningless.
#  2. The import must be pinned to the baseline's own src, with `-o pythonpath=<abs path>`,
#     and then ASSERTED — the harness checks that the imported module really lives under
#     the baseline worktree, and aborts if it does not.
#
# Usage: ./verify.sh <issue> <test-file-relative-to-v8-next> [extra pytest args...]
#   ./verify.sh 389 tests/test_cli_status_ledger_quarantine_389.py

set -uo pipefail

ISSUE="${1:?issue number required}"
TESTFILE="${2:?test file relative to v8-next/ required}"
shift 2 || true
EXTRA=("$@")

REPO_ROOT="C:/Users/dresden/Documents/v8"
BRANCH_WT="$REPO_ROOT/../v8-wt-${ISSUE}"
BASELINE_WT="$REPO_ROOT/../v8-wt-verify"
OUT="$REPO_ROOT/audit_out/critical_fixes_20261101/verify_${ISSUE}"
mkdir -p "$OUT"
LOG="$OUT/run.log"
: > "$LOG"

say() { echo "$*" | tee -a "$LOG"; }

[ -d "$BRANCH_WT/v8-next" ]   || { echo "missing branch worktree $BRANCH_WT"; exit 2; }
[ -d "$BASELINE_WT/v8-next" ] || { echo "missing baseline worktree $BASELINE_WT"; exit 2; }

say "=== #${ISSUE} — independent verification"

# --- guard: is the import really coming from the baseline checkout? -----------
cat > "$BASELINE_WT/v8-next/_which_src.py" <<'PY'
import v8_next, sys
print(v8_next.__file__)
PY
IMPORTED=$( cd "$BASELINE_WT/v8-next" && uv run python _which_src.py 2>/dev/null )
rm -f "$BASELINE_WT/v8-next/_which_src.py"
case "$IMPORTED" in
  *"v8-wt-verify"*) say "import pinned to baseline: $IMPORTED" ;;
  "")               say "ABORT: could not resolve which v8_next is imported"; exit 2 ;;
  *)                say "ABORT: baseline pytest would import $IMPORTED (not the baseline checkout)"
                    say "       refusing to certify a before/after that compares a branch to itself"
                    exit 2 ;;
esac

# --- 1) branch: the test must pass ------------------------------------------
say ""
say "--- branch  ($BRANCH_WT/v8-next/$TESTFILE)"
( cd "$BRANCH_WT/v8-next" && uv run pytest -q -o addopts="" "$TESTFILE" "${EXTRA[@]}" ) \
  > "$OUT/branch.txt" 2>&1
BRANCH_RC=$?
say "exit=$BRANCH_RC   $(tail -n 1 "$OUT/branch.txt")"

# --- 2) baseline: the same file must fail -----------------------------------
BASE_SRC="$BASELINE_WT/v8-next/$TESTFILE"
mkdir -p "$(dirname "$BASE_SRC")"
cp "$BRANCH_WT/v8-next/$TESTFILE" "$BASE_SRC"
COPIED=1
say ""
say "--- baseline main@a921da2  (test file copied in, pythonpath pinned)"
( cd "$BASELINE_WT/v8-next" && uv run pytest -q -o addopts="" \
    -o "pythonpath=$BASELINE_WT/v8-next/src" "$TESTFILE" "${EXTRA[@]}" ) \
  > "$OUT/baseline.txt" 2>&1
BASE_RC=$?
say "exit=$BASE_RC   $(tail -n 1 "$OUT/baseline.txt")"

# leftover copied test files must never be left dirty in the baseline
if [ "$COPIED" = 1 ]; then
  git -C "$BASELINE_WT" ls-files --error-unmatch "v8-next/$TESTFILE" >/dev/null 2>&1 \
    && git -C "$BASELINE_WT" checkout -- "v8-next/$TESTFILE" \
    || rm -f "$BASE_SRC"
fi

# --- verdict ----------------------------------------------------------------
say ""
if [ "$BRANCH_RC" -ne 0 ]; then
  say "VERDICT: FAIL — the regression test does not pass on the branch"
  exit 1
elif [ "$BASE_RC" -eq 0 ]; then
  say "VERDICT: FAIL — the regression test also passes on main, so it proves nothing"
  exit 1
else
  say "VERDICT: PASS — fails on main (exit $BASE_RC), passes on the branch (exit 0)"
  exit 0
fi
