#!/usr/bin/env python3
"""
Documentation Path-Reference Auditor (D-159 R2.4.2 / issue #330; Rules 5 and 44).

Phantom path citations are how an unproduced artifact acquires apparent
provenance. Issue #330 found that the English and Turkish decision registers, the
D-153 full-text spec header and the CHANGELOG all cited
`v8-core/tests/benchmark_fabric_adversarial.rs`, a file that has never existed in
this repository. That is not a typo class worth tolerating: a cited path is a
provenance claim, and an unresolvable provenance claim is the documentation-level
instance of exactly what the zero-tolerance anti-synthetic directive bans in code
("No fictitious artifact references. Every referenced artifact must be physically
produced and verified on disk").

This tool extracts every repository-path citation from `docs/**/*.md` and fails
unless each one is accounted for.

Failure semantics (issue #330 §14): an unresolved citation with no registered
disposition is `BLOCKED / OPEN_PIN`, which here means exit 1.

Disposition classes, in evaluation order. Only the last one fails:

1. `RESOLVED` — the citation exists on disk. It may name a file, a directory, or
   the canonical `foo.rs` spelling of a directory-based module `foo/mod.rs`.
2. `RUNTIME_OUTPUT` — the cited artifact is *written by code* rather than tracked
   as source. Membership is proven, not asserted: the basename of the citation
   must literally appear in `v8-core/src/**.rs` or `tools/*.py`, or the path must
   be matched by `.gitignore` (`git check-ignore`). Reproducibly produced paths
   are not invented paths, so they are counted and listed but never asserted to
   exist. `git check-ignore` is used instead of a hand-written directory list so
   this class cannot drift from `.gitignore` itself.
3. `HISTORICAL_RECORD` — the citation sits inside a dated CHANGELOG entry earlier
   than `LIVE_HISTORY_CUTOFF`. A changelog entry records what was believed at its
   own date, including that date's path layout; rewriting old entries to match
   today's tree would destroy the evidence, which is the opposite of #330's
   purpose. The newest entries remain live and are checked normally, so a fresh
   phantom reference gets no free pass merely because the file is a changelog.
4. `RETIRED` — the path is absent from the tree but provably existed in this
   repository's git history (`git log --all --diff-filter=A`). This is stale
   documentation about a real predecessor, which is a *different* fault from
   fabrication: the citation names an artifact that was physically produced and
   later removed. Retired citations are listed for follow-up and pass.
5. `ROOT_DECLARED` — a document may declare search roots with
   `<!-- AUDIT-DOC-PATHS: ROOT <dir> -->`, which licenses *relative* resolution
   under those roots only. `IMPLEMENTATION_LAYOUT.md` §1 keys its table rows by
   module name relative to the frozen Python oracle package, so it declares
   `src/v8`. This is a per-file, greppable, reviewable statement; the classifier
   never tries to guess a root, because suffix-matching an invented path against
   arbitrary subtrees is precisely the kind of silent acceptance this guard exists
   to prevent.
6. `ALLOWED` — the line carries an explicit marker of the form
   `<!-- AUDIT-DOC-PATHS: <CLASS> <reason> -->`. This is how a *deliberate*
   negative, planned or foreign citation is expressed: "this file never existed",
   "`tests/parity.rs` was designed but never built", "these are V7 materials in a
   predecessor repository", "this output is specified but not yet emitted". The
   marker is per-line and carries a reason naming the exact citation it covers,
   so the exemption is itself auditable. A marker whose paths all resolve is
   reported as stale, so exemptions cannot outlive their purpose.
7. `UNACCOUNTED` — everything else. Exit 1.

Extraction is deliberately conservative: a token counts as a path citation only
when it is a backticked code span that looks like a repository path. That excludes
English and Turkish prose, git object ids, commit shas, branch names, dotted
identifiers (`AppendOnlyLog.append/read/replay_tape`), spec coordinates, math
fragments, URLs, absolute paths and bare filenames. A guard that must be disabled
because it drowns in prose is worth nothing, so classification is strict by
construction rather than by an exemption list.
"""

import os
import re
import subprocess
import sys
from collections import defaultdict

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC_ROOTS = ("docs",)
DOC_EXTS = (".md",)

# Live normative history floor for CHANGELOG entries. Entries dated on or after
# this are audited like any other document; earlier entries are HISTORICAL_RECORD.
# This is the date of the D-159 governance reconciliation itself.
LIVE_HISTORY_CUTOFF = "2026-09-07"
HISTORY_FILE_RE = re.compile(r"(^|/)CHANGELOG\.md$")
DATE_HEADING_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})")

# Source surfaces that *write* artifacts are how RUNTIME_OUTPUT is proven.
CODE_GLOBS = (("v8-core", "src", ".rs"), ("tools", None, ".py"))

# Only these extensions are unambiguous enough to call a token a file citation.
PATH_EXTS = (
    ".rs", ".py", ".md", ".toml", ".json", ".jsonl", ".html", ".yaml", ".yml",
    ".txt", ".csv", ".parquet", ".lock", ".sh", ".pdf", ".sql",
)

# Inline code spans. The lookarounds prevent matching inside fenced blocks or
# double-backtick spans, so nested markup cannot smuggle in a false token.
CODE_SPAN = re.compile(r"(?<!`)`{1,2}(?!`)([^`\n]+?)(?<!`)`(?!`)")

# Characters that make a token prose, a diff marker, a spec coordinate, a glob,
# an interpolation or a type expression rather than a filesystem path.
REJECT_CHARS = set(' \t*?<>|{}()=+^&%@;,"\'!#`')
REJECT_PREFIXES = ("http://", "https://", "git@", "ssh://", "s3://", "file://",
                   "$", "~", "/", "./", "../", "arXiv:", "urn:", "mailto:", "@@")

# Per-line registered exception marker, e.g.
#   <!-- AUDIT-DOC-PATHS: DESIGN_REFERENCE tests/parity.rs was never built -->
ALLOW_MARKER = re.compile(
    r"<!--\s*AUDIT-DOC-PATHS:\s*(?P<cls>[A-Z_]+)\s+(?P<reason>[^\n]*?)\s*-->"
)
ROOT_MARKER = re.compile(r"<!--\s*AUDIT-DOC-PATHS:\s*ROOT\b[^>]*-->")


def iter_doc_files(doc_roots=DOC_ROOTS):
    for root in doc_roots:
        for dirpath, dirnames, filenames in os.walk(os.path.join(REPO_ROOT, root)):
            dirnames[:] = sorted(d for d in dirnames
                                 if d not in {".git", "__pycache__", "node_modules"})
            for name in sorted(filenames):
                if name.endswith(DOC_EXTS):
                    yield os.path.relpath(os.path.join(dirpath, name), REPO_ROOT)


def is_path_citation(token):
    """Strict classifier, conservative enough that prose never counts as a path."""
    t = token.strip()
    if not t or t.startswith(REJECT_PREFIXES):
        return False
    if any(ch in REJECT_CHARS for ch in t):
        return False
    core = t.rstrip("/")
    if "/" not in core:
        return False                                  # bare filenames: not citations
    if not (core.endswith(PATH_EXTS) or t.endswith("/")):
        return False                                  # no ext and no trailing slash
    for seg in [s for s in core.split("/") if s]:
        if seg[:1].isupper():
            return False                              # `Order/Fill/Position`
        if re.fullmatch(r"[0-9._\-]+", seg):
            return False                              # `0.8906/0.9415`, `phase1/2/3`
    return True


def candidate_forms(token, roots=()):
    """A citation may name a file, a directory, or the canonical spelling of a
    directory-based module (`foo.rs` for `foo/mod.rs`), and may additionally be
    relative to a root the citing document has declared."""
    t = token.rstrip("/")
    forms = [t]
    if os.path.isdir(os.path.join(REPO_ROOT, t)):
        forms.append(t + "/mod.rs")
    if t.endswith(".rs"):
        forms.append(t[:-3] + "/mod.rs")
    for root in roots:
        root = root.rstrip("/")
        forms.extend(os.path.join(root, f) for f in list(forms))
    return forms


def collect_code_text():
    """Concatenated source of the surfaces that write artifacts, so a cited
    runtime output path can be matched against a literal in code rather than
    against a hand-maintained allowlist."""
    chunks = []
    for root, sub, ext in CODE_GLOBS:
        base = os.path.join(REPO_ROOT, root)
        if sub:
            base = os.path.join(base, sub)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in {"target", ".git"}]
            for fname in sorted(filenames):
                if not fname.endswith(ext):
                    continue
                # This auditor necessarily names the phantom paths it exists to
                # catch. Reading itself as "producer code" would let the guard
                # launder its own examples into RUNTIME_OUTPUT.
                if fname == os.path.basename(__file__):
                    continue
                path = os.path.join(dirpath, fname)
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as fh:
                        chunks.append(fh.read())
                except OSError:
                    continue
    return "\n".join(chunks)


SOURCE_EXTS = (".rs", ".py", ".md", ".toml", ".sh")
SOURCE_PREFIXES = ("v8-core/src/", "src/v8/", "src/", "tools/", "docs/", "v8-core/tests/")


def is_source_like(core):
    """Code and documentation are never runtime output: an absent source file is
    either a retired predecessor (provable in git history) or unaccounted for."""
    base = os.path.basename(core)
    if base.endswith(SOURCE_EXTS):
        return True
    return core.startswith(SOURCE_PREFIXES)


class Prover:
    """Answers existence questions about the tree and its git history."""

    def __init__(self):
        self._cache = {}
        self.emitted = None  # retained for clarity; matching uses code_text()

    def exists(self, token, roots=()):
        key = ("exists", token, tuple(roots))
        if key not in self._cache:
            self._cache[key] = any(
                os.path.exists(os.path.join(REPO_ROOT, f)) for f in candidate_forms(token, roots)
            )
        return self._cache[key]

    def git_ignored(self, path):
        key = ("ignored", path)
        if key not in self._cache:
            proc = subprocess.run(["git", "check-ignore", "-q", "--", path],
                                  cwd=REPO_ROOT, capture_output=True)
            self._cache[key] = proc.returncode == 0
        return self._cache[key]

    def ever_existed(self, path):
        key = ("history", path)
        if key not in self._cache:
            proc = subprocess.run(
                ["git", "log", "--all", "--diff-filter=A", "--format=%h", "-1", "--", path],
                cwd=REPO_ROOT, capture_output=True, text=True,
            )
            self._cache[key] = bool(proc.stdout.strip())
        return self._cache[key]

    def code_text(self):
        if "_blob" not in self._cache:
            self._cache["_blob"] = collect_code_text()
        return self._cache["_blob"]

    def runtime_output(self, token):
        core = token.rstrip("/")
        if not core:
            return False
        # Source files are never "runtime output". A cited `.rs` / `.py` / `.md`
        # that is absent is either retired (provable in history) or unaccounted
        # for; letting it be excused because its name appears in some string
        # literal would be exactly the false acceptance this guard exists to
        # prevent. Empirically this mattered: `v8-core/src/runloop/` and
        # `src/data.rs` were about to be excused as runtime artifacts merely
        # because those strings occur in code.
        if is_source_like(core):
            return False
        # The cited path itself, or something deeper beneath it, is a literal
        # string in repository code: the artifact is written at runtime and is
        # therefore not present in a tracked checkout. Matched on the *cited
        # path*, not on its basename, so an invented `foo/bar.json` cannot borrow
        # the standing of an unrelated emitted `bar.json`.
        blob = self.code_text()
        if core in blob or (core + "/") in blob:
            return True
        parent = os.path.dirname(core)
        if parent and self.git_ignored(parent + "/"):
            return True
        return self.git_ignored(core)


def audit(doc_roots=DOC_ROOTS, quiet=False, prove=None):
    """Run the audit over a set of document roots. Returns (exit_code, stats)."""
    prove = prove or Prover()

    checked = 0
    files_scanned = 0
    counts = defaultdict(int)
    unaccounted = defaultdict(list)
    allowed = defaultdict(list)
    retired = defaultdict(list)
    runtime = defaultdict(list)

    for rel_doc in iter_doc_files(doc_roots):
        files_scanned += 1
        is_history = bool(HISTORY_FILE_RE.search(rel_doc))
        entry_is_historical = False
        text = _read(rel_doc)
        lines = text.split("\n")
        # Per-file declared roots (see module docstring, ROOT_DECLARED).
        roots = tuple(_declared_roots(text))
        for lineno, line in enumerate(lines, start=1):
            head = DATE_HEADING_RE.match(line)
            if head:
                entry_is_historical = (is_history
                                       and head.group(1) < LIVE_HISTORY_CUTOFF)
            markers = ALLOW_MARKER.findall(line)
            cited = [t.strip() for t in CODE_SPAN.findall(line)
                     if is_path_citation(t.strip())]
            if not cited and not markers:
                continue
            for token in cited:
                checked += 1
                if prove.exists(token, roots):
                    counts["RESOLVED"] += 1
                    continue
                if any(tok == token for tok in _marker_tokens(line)):
                    counts["ALLOWED"] += 1
                    allowed[token].append((rel_doc, lineno, dict(
                        (c, r) for c, r in markers)))
                    continue
                if prove.runtime_output(token):
                    counts["RUNTIME_OUTPUT"] += 1
                    runtime[token].append((rel_doc, lineno))
                    continue
                if entry_is_historical:
                    counts["HISTORICAL_RECORD"] += 1
                    continue
                core = token.rstrip("/")
                if prove.ever_existed(core):
                    counts["RETIRED"] += 1
                    retired[token].append((rel_doc, lineno))
                    continue
                counts["UNACCOUNTED"] += 1
                unaccounted[token].append((rel_doc, lineno))

        # Stale-marker sweep: an ALLOWED marker whose cited paths all resolve is
        # no longer an exemption and should be deleted.
        for lineno, line in enumerate(lines, start=1):
            if not ALLOW_MARKER.search(line) or ROOT_MARKER.search(line):
                continue
            toks = _marker_tokens(line)
            if toks and all(prove.exists(t, roots) for t in toks):
                counts["STALE_MARKER"] += 1
                allowed.setdefault("<stale>", []).append((rel_doc, lineno, line.strip()[:80]))

    stats = {
        "files": files_scanned, "checked": checked, "counts": dict(counts),
        "unaccounted": dict(unaccounted), "retired": dict(retired),
        "runtime": dict(runtime), "allowed": dict(allowed),
    }
    if quiet:
        return (1 if unaccounted else 0), stats

    print("=" * 70)
    print(">>> DOCUMENTATION PATH-REFERENCE AUDIT (D-159 R2.4.2 / Rules 5, 44) <<<")
    print("=" * 70)
    print(f"markdown files scanned        : {files_scanned}")
    print(f"path citations audited        : {checked}")
    print(f"  RESOLVED                    : {counts['RESOLVED']}")
    print(f"  RUNTIME_OUTPUT              : {counts['RUNTIME_OUTPUT']} distinct {len(runtime)}")
    print(f"  HISTORICAL_RECORD           : {counts['HISTORICAL_RECORD']}")
    print(f"  RETIRED (existed in history): {counts['RETIRED']} distinct {len(retired)}")
    print(f"  ALLOWED (marked)            : {counts['ALLOWED']} distinct {len(allowed)}")
    print(f"  UNACCOUNTED (failing)       : {counts['UNACCOUNTED']} distinct {len(unaccounted)}")
    if counts["STALE_MARKER"]:
        print(f"  STALE_MARKER (delete it)    : {counts['STALE_MARKER']}")
        for tok, hits in sorted(allowed.items()):
            if tok == "<stale>":
                for rel_doc, lineno, snippet in hits:
                    print(f"      {rel_doc}:{lineno}: {snippet}")

    if retired:
        print("\nRETIRED citations (real predecessors, absent from the current tree;"
              " documentation staleness, not fabrication):")
        for tok, hits in sorted(retired.items()):
            print(f"  {tok}")
            for rel_doc, lineno in hits[:3]:
                print(f"      {rel_doc}:{lineno}")
            if len(hits) > 3:
                print(f"      ... and {len(hits) - 3} more site(s)")

    if runtime:
        print("\nRUNTIME_OUTPUT citations (produced by code, not tracked as source):")
        for tok in sorted(runtime):
            print(f"  {tok}  ({len(runtime[tok])} site(s))")

    if unaccounted:
        print("\nUNACCOUNTED PATH CITATIONS:")
        for tok in sorted(unaccounted):
            hits = unaccounted[tok]
            print(f"  {tok}")
            for rel_doc, lineno in hits[:8]:
                print(f"      {rel_doc}:{lineno}")
            if len(hits) > 8:
                print(f"      ... and {len(hits) - 8} more site(s)")
        print("""
FAIL: a cited repository path is unaccounted for.

Every cited path must be RESOLVED on disk, or be a runtime artifact that code
actually writes, or be a historical changelog record, or name a predecessor that
existed in git history, or carry an explicit per-line
`<!-- AUDIT-DOC-PATHS: <CLASS> <reason> -->` marker.

A path that has never existed anywhere in this tree or its history and is not
registered as a deliberate negative/design citation is a fabricated provenance
claim (AGENTS.md anti-synthetic directive §5; D-159 R2.4.2). Correct the citation,
produce the artifact, or mark the line with its reason. Do not weaken this guard.""")
        return 1, stats

    print("\nPASS: every audited documentation path citation is accounted for.")
    return 0, stats


PHANTOM_CITATION = "v8-core/tests/benchmark_fabric_adversarial.rs"


def self_test(prove):
    """Negative check: the guard must actually catch a fabricated citation.

    A guard that silently accepts everything looks identical to a working guard
    until something tests it, which is how #330's phantom test path survived in
    three governance documents. Issue #330's verification gate demands a negative
    check for nonexistent test paths, so this auditor verifies its own detection
    instead of asserting it.
    """
    import shutil
    import tempfile

    failures = []
    real_root = REPO_ROOT
    scratch = tempfile.mkdtemp(prefix="audit-doc-path-selftest-")
    try:
        cases = [
            # (name, document body, expected exit code)
            ("phantom-cited-as-existing",
             "See `%s` for the suite.\n" % PHANTOM_CITATION, 1),
            ("phantom-marked-as-never-existed",
             "It cited `%s`, which never existed. "
             "<!-- AUDIT-DOC-PATHS: NEGATIVE_CITATION `%s` never existed. -->\n"
             % (PHANTOM_CITATION, PHANTOM_CITATION), 0),
            ("real-path-cited",
             "See `src/real.rs` and `notes/`.\n", 0),
            ("bare-identifier-not-a-path",
             "Uses `Order/Fill` semantics and `0.89/0.94` bands.\n", 0),
            ("invented-source-file",
             "Lives in `v8-core/src/benchmark/does_not_exist_at_all.rs`.\n", 1),
        ]
        for name, body, expected in cases:
            root = os.path.join(scratch, name)
            os.makedirs(os.path.join(root, "docs"), exist_ok=True)
            # Fixtures that expect a citation to resolve need the file to exist
            # *inside the scratch repo*, not merely somewhere in the real tree;
            # that distinction is what makes the negative cases meaningful.
            os.makedirs(os.path.join(root, "src"), exist_ok=True)
            os.makedirs(os.path.join(root, "notes"), exist_ok=True)
            with open(os.path.join(root, "src", "real.rs"), "w",
                      encoding="utf-8") as fh:
                fh.write("fn main() {}\n")
            with open(os.path.join(root, "docs", "case.md"), "w",
                      encoding="utf-8") as fh:
                fh.write(body)
            # REPO_ROOT is read as a module global by the helpers, so it must be
            # swapped for the fixture and restored from a value captured *before*
            # the swap. Restoring from the global itself would restore the
            # fixture path and silently audit the wrong repository afterwards.
            cwd = os.getcwd()
            try:
                os.chdir(root)
                globals()["REPO_ROOT"] = root
                code, _ = audit(doc_roots=("docs",), quiet=True, prove=prove)
            finally:
                os.chdir(cwd)
                globals()["REPO_ROOT"] = real_root
            status = "ok" if code == expected else "FAIL"
            if code != expected:
                failures.append("%s: expected exit %d, got %d" % (name, expected, code))
            print(f"  self-test {name:38s} exit={code} expected={expected}  [{status}]")

        # The headline phantom must not exist in the real tree, or the negative
        # citation markers above are marking a path that should simply resolve.
        if os.path.exists(os.path.join(real_root, PHANTOM_CITATION)):
            failures.append("%s now exists; remove the NEGATIVE_CITATION markers"
                            % PHANTOM_CITATION)
        else:
            print(f"  self-test phantom-absent                         "
                  f"[ok] {PHANTOM_CITATION} is not in the tree")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    if failures:
        for f in failures:
            print("  SELF-TEST FAIL:", f)
        return 1
    print("  self-test: all cases behaved as expected")
    return 0


def main():
    os.chdir(REPO_ROOT)
    argv = sys.argv[1:]
    prove = Prover()
    if "--self-test" in argv:
        print(">>> audit_doc_path_refs self-test (negative detection check) <<<")
        rc = self_test(prove)
        if rc:
            return rc
        print()
    code, _stats = audit(prove=prove)
    return code


def _read(rel_doc):
    with open(rel_doc, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _declared_roots(text):
    """Directories licensed by `<!-- AUDIT-DOC-PATHS: ROOT <dir> -->`."""
    out = []
    for m in ALLOW_MARKER.finditer(text):
        cls, reason = m.group("cls"), m.group("reason")
        if cls.upper() != "ROOT":
            continue
        for tok in re.findall(r"[A-Za-z0-9._\-/]+", reason):
            if os.path.isdir(os.path.join(REPO_ROOT, tok.rstrip("/"))):
                out.append(tok.rstrip("/"))
    return sorted(set(out))


def _marker_tokens(line):
    """The citation each marker comment exempts.

    A marker covers exactly one path, named as the *first* backticked span of its
    reason. The strict grammar exists so an exemption can never silently widen to
    sibling citations sharing the line: a reason that explains one phantom must
    not become a blanket for whatever else is on that line. Multi-path lines carry
    one marker per path.
    """
    out = []
    for m in ALLOW_MARKER.finditer(line):
        if m.group("cls").upper() == "ROOT":
            continue
        spans = re.findall(r"`([^`]+)`", m.group("reason"))
        if spans and is_path_citation(spans[0].strip()):
            out.append(spans[0].strip())
    return [t for t in out if t]


if __name__ == "__main__":
    sys.exit(main())
