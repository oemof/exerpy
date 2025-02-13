import os
import sys


__ebsilon_path__ = os.getenv("EBS")

if __ebsilon_path__ is not None:

    sys.path.append(__ebsilon_path__)

    try:
        import EbsOpen
    except ModuleNotFoundError:
        msg = (
            "Could not find EbsOpen in the path specified by the 'EBS' "
            "environment variables."
        )
        raise ModuleNotFoundError(msg)
