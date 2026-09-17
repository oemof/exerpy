"""
Shared pytest configuration.

The plotting tests must not depend on an interactive matplotlib backend: a GUI backend needs a
working Tk installation and a display, which is not given on CI or in every editor's test runner.
Selecting the non-interactive Agg backend here makes the tests behave the same way regardless of
how they are started. The tox environments set MPLBACKEND=Agg for the same reason.
"""

import matplotlib

matplotlib.use("Agg")
