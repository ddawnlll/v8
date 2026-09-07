#!/bin/bash
# Enumerate libtest harnesses among built deps binaries.
cd /Users/hootie/src/v8/.worktrees/v86-exec || exit 1
: > .audit/w6/harnesses.txt
for b in v8-core/target/debug/deps/*; do
  [ -f "$b" ] || continue
  [ -x "$b" ] || continue
  n=$(basename "$b")
  case "$n" in
    *.*) continue ;;
  esac
  first=$("$b" 2>&1 | head -n 3 | tr '\n' '|')
  case "$first" in
    *running*tests*) echo "$b :: $first" >> .audit/w6/harnesses.txt ;;
  esac
done
echo "done"
