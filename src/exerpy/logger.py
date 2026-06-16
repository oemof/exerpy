"""Module for logging specification.

Provides a dedicated ``exerpy`` logger instead of using the root logger
directly, so importing/using exerpy does not implicitly configure logging
for other libraries (e.g. TESPy) sharing the same process.
"""

import logging

logger = logging.getLogger("exerpy")
logger.addHandler(logging.NullHandler())
