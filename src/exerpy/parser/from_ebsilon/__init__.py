import os
import sys
from typing import Optional

# Define the path to Ebsilon from environment variable
__ebsilon_path__ = os.getenv("EBS")

# Flag to indicate if Ebsilon is available
__ebsilon_available__ = False

if __ebsilon_path__ is not None:
    # Add the Ebsilon path to the system path
    sys.path.append(__ebsilon_path__)

    try:
        # Try to import EbsOpen
        import EbsOpen

        # Set the availability flag to True if import succeeds
        __ebsilon_available__ = True
    except ImportError:
        # Give a clear error message with guidance
        msg = (
            "Could not find EbsOpen in the path specified by the 'EBS' "
            "environment variable. Please ensure the path is correct and "
            "points to a valid Ebsilon installation."
        )
        print(f"Warning: {msg}")


def is_ebsilon_available() -> bool:
    """
    Check if Ebsilon functionality is available.
    
    Returns:
        bool: True if Ebsilon is available, False otherwise.
    """
    return __ebsilon_available__