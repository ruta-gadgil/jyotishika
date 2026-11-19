"""Strict parsing of query-string parameters."""
from typing import Mapping, Optional


def parse_int_param(
    args: Mapping[str, str],
    name: str,
    default: Optional[int],
    minimum: int,
    maximum: Optional[int] = None,
) -> Optional[int]:
    """
    Read an integer query parameter made of digits only.

    Args:
        args: query parameters (e.g. flask `request.args`)
        name: parameter name
        default: value returned when the parameter is absent (may be None)
        minimum: smallest allowed value
        maximum: largest allowed value, or None for no upper bound

    Returns:
        The parsed integer, or `default` when the parameter is absent.

    Raises:
        ValueError: with a message naming the parameter, if the value is not
            an integer within [minimum, maximum]. Signs, floats, blanks and
            non-ASCII digits are all rejected.
    """
    raw = args.get(name)
    if raw is None:
        return default

    if maximum is None:
        expectation = f"an integer >= {minimum}"
    else:
        expectation = f"an integer between {minimum} and {maximum}"

    if not raw.isascii() or not raw.isdigit():
        raise ValueError(f"{name} must be {expectation}")

    value = int(raw)
    if value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f"{name} must be {expectation}")
    return value
