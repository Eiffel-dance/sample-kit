import json
import math
import numbers
import random

_SEED_TYPES = (type(None), int, float, str, bytes, bytearray)


def _is_sized_sequence(value):
    return hasattr(value, "__len__") and hasattr(value, "__getitem__")


def weighted_sample(items, weights, k, seed=0):
    """Deterministically draw k items without replacement, weighted by position.

    Validation happens fully before any sampling; failures raise before a
    single element is drawn, so no partial result can escape. Valid calls
    keep the original selection order, zero-weight and duplicate semantics,
    and never mutate the caller's items or weights.
    """
    if not _is_sized_sequence(items):
        raise TypeError("items must be a sequence with a determinable length")
    if not _is_sized_sequence(weights):
        raise TypeError("weights must be a sequence with a determinable length")
    if isinstance(k, bool) or not isinstance(k, int):
        raise TypeError("k must be a non-boolean integer")
    if not isinstance(seed, _SEED_TYPES):
        raise TypeError("seed must be None, int, float, str, bytes, or bytearray")
    if len(items) != len(weights):
        raise ValueError("items and weights must have equal lengths")
    if k < 0 or k > len(items):
        raise ValueError("invalid sample size")
    checked = []
    for w in weights:
        if isinstance(w, bool) or not isinstance(w, numbers.Real):
            raise TypeError("every weight must be a real number")
        if not math.isfinite(w):
            raise ValueError("every weight must be finite")
        if w < 0:
            raise ValueError("negative weight")
        checked.append(w)
    pool = list(zip(items, checked))
    out = []
    rng = random.Random(seed)
    for _ in range(k):
        total = sum(w for _, w in pool)
        if total <= 0:
            raise ValueError("no positive weight")
        needle = rng.random() * total
        acc = 0
        for i, (item, w) in enumerate(pool):
            acc += w
            if needle < acc:
                out.append(item)
                pool.pop(i)
                break
    return out


def _validate_json_tree(value, active):
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("NaN and Infinity are not JSON-representable")
        return
    if isinstance(value, (list, tuple)):
        ident = id(value)
        if ident in active:
            raise TypeError("circular reference is not JSON-representable")
        active.add(ident)
        for element in value:
            _validate_json_tree(element, active)
        active.discard(ident)
        return
    if isinstance(value, dict):
        ident = id(value)
        if ident in active:
            raise TypeError("circular reference is not JSON-representable")
        active.add(ident)
        for key, element in value.items():
            if isinstance(key, float) and not math.isfinite(key):
                raise ValueError("NaN and Infinity are not JSON-representable")
            _validate_json_tree(element, active)
        active.discard(ident)
        return
    raise TypeError(
        "object of type %s is not JSON-representable" % type(value).__name__
    )


def serialize_metrics(metrics):
    """Serialize a metrics tree to compact, key-sorted JSON text.

    Integers of any size are emitted as exact decimal text (never via
    floats or scientific notation). NaN/Infinity raise ValueError; sets,
    circular references, and other unrepresentable values raise TypeError.
    """
    _validate_json_tree(metrics, set())
    return json.dumps(metrics, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)
