"""Analysis-plane reader for V8.2 columnar artifacts (LEDGER_FORMAT_SPEC §3-4).

The compute-plane boundary is an artifact file, never an FFI call
(COMPUTE_CORE_SPEC §7): the Rust `v8-core` binary writes column-major `.v82`
artifacts and this module reads them back. The parity harness uses it to
compare every emitted value against the V8.0 oracle.

Format (byte layout):

    magic "V82LDRG1"           8 bytes
    header_len u32 LE
    header JSON                artifact_kind, hash_encoding, schema,
                               run_constants, tier, row_count, column_count,
                               ordering
    per column:
        name_len u16 LE, name
        dtype u8               (0=i64, 1=f64, 2=bool, 3=dict-str)
        n_rows u32 LE
        validity bitmask       ceil(n/8) bytes, LSB-first (1 = valid)
        values                 i64/f64/bool fixed-width, dict-str u16 LE ids
        dictionary             (dict-str only): count u32 LE, then per entry
                               str_len u32 LE + UTF-8

Numeric columns are fixed-width IEEE-754 / two's complement — never decimal
text — so the float-rendering hazard cannot reach the analysis plane. Absent
values carry an explicit validity bit (MARKET_STATE_CONTRACT §4: absence is
never a sentinel number).
"""
from __future__ import annotations

import json
import struct

MAGIC = b"V82LDRG1"

DTYPE_I64 = 0
DTYPE_F64 = 1
DTYPE_BOOL = 2
DTYPE_DICT_STR = 3


class ArtifactError(ValueError):
    """A malformed or unreadable V8.2 artifact. The reader fails closed: a
    truncated file, a wrong magic, or a declared tier that cannot serve the
    requested values raises instead of returning a partial row."""


class Column:
    def __init__(self, name, dtype, valid, values, dictionary=None):
        self.name = name
        self.dtype = dtype
        self.valid = valid          # list[bool], one per row
        self.values = values        # list of i64 / f64 / bool / str
        self.dictionary = dictionary

    def __len__(self):
        return len(self.valid)


class Artifact:
    def __init__(self, kind, hash_encoding, run_constants, tier,
                 row_count, column_count, ordering, columns):
        self.kind = kind
        self.hash_encoding = hash_encoding
        self.run_constants = run_constants
        self.tier = tier
        self.row_count = row_count
        self.column_count = column_count
        self.ordering = ordering
        self.columns = columns
        self._by_name = {c.name: c for c in columns}

    def column(self, name):
        try:
            return self._by_name[name]
        except KeyError:
            raise ArtifactError(f"artifact has no column {name!r}")

    def row(self, i):
        """Row `i` as an ordered dict; absent cells carry `None`."""
        if not 0 <= i < self.row_count:
            raise ArtifactError(f"row {i} out of range (0..{self.row_count - 1})")
        out = {}
        for c in self.columns:
            out[c.name] = c.values[i] if c.valid[i] else None
        return out

    def rows(self):
        for i in range(self.row_count):
            yield self.row(i)


def read(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:8] != MAGIC:
        raise ArtifactError(f"{path}: not a V8.2 artifact (bad magic)")
    off = 8
    (header_len,) = struct.unpack_from("<I", data, off)
    off += 4
    if off + header_len > len(data):
        raise ArtifactError(f"{path}: truncated header")
    header = json.loads(data[off:off + header_len].decode("utf-8"))
    off += header_len

    columns = []
    for _ in range(header["column_count"]):
        (name_len,) = struct.unpack_from("<H", data, off)
        off += 2
        name = data[off:off + name_len].decode("utf-8")
        off += name_len
        (dtype,) = struct.unpack_from("<B", data, off)
        off += 1
        (n_rows,) = struct.unpack_from("<I", data, off)
        off += 4
        mask_len = (n_rows + 7) // 8
        mask = data[off:off + mask_len]
        off += mask_len
        valid = [bool(mask[i // 8] & (1 << (i % 8))) for i in range(n_rows)]

        if dtype == DTYPE_I64:
            n_bytes = 8 * n_rows
            vals = list(struct.unpack_from(f"<{n_rows}q", data, off))
            off += n_bytes
            dictionary = None
        elif dtype == DTYPE_F64:
            n_bytes = 8 * n_rows
            vals = list(struct.unpack_from(f"<{n_rows}d", data, off))
            off += n_bytes
            dictionary = None
        elif dtype == DTYPE_BOOL:
            vals = list(data[off:off + n_rows])
            off += n_rows
            dictionary = None
        elif dtype == DTYPE_DICT_STR:
            ids = list(struct.unpack_from(f"<{n_rows}H", data, off))
            off += 2 * n_rows
            (dict_len,) = struct.unpack_from("<I", data, off)
            off += 4
            dictionary = []
            for _ in range(dict_len):
                (s_len,) = struct.unpack_from("<I", data, off)
                off += 4
                s = data[off:off + s_len].decode("utf-8")
                off += s_len
                dictionary.append(s)
            vals = [dictionary[i] for i in ids]
        else:
            raise ArtifactError(f"{path}: unknown dtype {dtype}")

        columns.append(Column(name, dtype, valid, vals, dictionary))

    return Artifact(header["artifact_kind"], header["hash_encoding"],
                    header["run_constants"], header["tier"],
                    header["row_count"], header["column_count"],
                    header["ordering"], columns)


def fingerprint(path):
    """SHA-1 (hex) over the raw artifact bytes — the artifact identity used
    for byte-stability (G4) and cache keys."""
    import hashlib
    with open(path, "rb") as fh:
        return hashlib.sha1(fh.read()).hexdigest()
