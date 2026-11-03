"""Parsers that read the models of simulation tools into ExerPy's input format."""

#: Temperature step in K below and above a stream's temperature for :func:`state_between`.
STATE_CHECK_STEP = 0.05


def state_between(h, s, below, above, rtol=1e-7):
    """
    Whether the enthalpy ``h`` and entropy ``s`` of a stream lie between their values ``below`` and ``above``.

    ``below`` and ``above`` are (h, s) at the stream's pressure and its temperature minus and plus
    :data:`STATE_CHECK_STEP`, from the property calculation that splits the physical exergy. The stream's own
    values lie between them, also when it is saturated or two-phase, unless the split uses other property
    data than the simulator used for the stream.

    >>> state_between(100.0, 1.0, (99.9, 0.99), (100.1, 1.01)), state_between(100.0, 1.0, (100.1, 1.0), (100.2, 1.0))
    (True, False)
    """
    if None in (h, s, *below, *above):
        return False
    return all(
        min(lo, hi) - rtol * abs(x) <= x <= max(lo, hi) + rtol * abs(x)
        for x, lo, hi in zip((h, s), below, above, strict=True)
    )
