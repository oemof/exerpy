"""Module for logging specification.

Provides a dedicated ``exerpy`` logger instead of using the root logger directly,
so using exerpy does not configure logging for other libraries (e.g. TESPy) sharing
the same process.

No ``NullHandler`` is attached: exerpy's own warnings are therefore visible by
default through the standard library's last-resort handler (WARNING and above on
stderr), without the user having to configure logging. Records still propagate, so
once an application configures logging (or pytest's ``caplog`` is active) they are
captured and formatted there instead.
"""

import logging

logger = logging.getLogger("exerpy")
