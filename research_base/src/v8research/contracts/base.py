"""Record base: serialisation and content addressing for every artifact."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar

from ..ids import content_hash

T = TypeVar("T", bound="Record")


class Record:
    """Base for all persisted artifacts.

    Deliberately not a dataclass itself: `Finding` must be frozen, and a frozen
    dataclass cannot inherit from a non-frozen one. This class contributes only
    behaviour and ClassVars, so subclasses are free to choose their mutability.

    `HASH_EXCLUDE` names fields that must not participate in the content hash:
    timestamps and mutable status fields would otherwise make an artifact's
    identity depend on when it was written rather than what it says.
    """

    if TYPE_CHECKING:
        __dataclass_fields__: ClassVar[dict[str, dataclasses.Field]]

    HASH_EXCLUDE: ClassVar[frozenset[str]] = frozenset(
        {"content_hash", "asserted_at", "timestamp", "created_at"}
    )
    KIND: ClassVar[str] = "record"

    def to_dict(self) -> dict[str, Any]:
        return _plain(dataclasses.asdict(self))

    def hashable_payload(self) -> dict[str, Any]:
        return {k: v for k, v in self.to_dict().items() if k not in self.HASH_EXCLUDE}

    def compute_hash(self) -> str:
        return content_hash(self.hashable_payload())

    @classmethod
    def from_dict(cls: type[T], payload: dict[str, Any]) -> T:
        known = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in payload.items() if k in known})


def _plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, frozenset):
        return sorted(_plain(v) for v in value)
    return value
