"""
Utilities to check Ebsilon installation.

This module provides functions to check the Ebsilon installation
and validate the EBS environment variable.
"""
import logging
import os
import sys
from typing import Optional
from typing import Tuple

from exerpy.parser.from_ebsilon import __ebsilon_available__
from exerpy.parser.from_ebsilon import __ebsilon_path__


def check_ebsilon_installation() -> Tuple[bool, Optional[str]]:
    """
    Check if Ebsilon is correctly installed and available.
    
    Returns:
        Tuple[bool, Optional[str]]: A tuple containing:
            - A boolean indicating if Ebsilon is available
            - A string with a message explaining the status (or None if available)
    """
    # Check if the EBS environment variable is set
    if __ebsilon_path__ is None:
        return False, "The EBS environment variable is not set."
    
    # Check if the path exists
    if not os.path.exists(__ebsilon_path__):
        return False, f"The path specified by EBS environment variable does not exist: {__ebsilon_path__}"
    
    # Check if EbsOpen can be imported
    if not __ebsilon_available__:
        return False, "EbsOpen module could not be imported. Please check your Ebsilon installation."
    
    # All checks passed
    return True, None


def validate_ebsilon_requirements() -> None:
    """
    Validate that all requirements for using Ebsilon functionality are met.
    
    Prints status messages and usage instructions.
    
    Raises:
        RuntimeError: If running on a non-Windows platform.
    """
    # Check if running on Windows
    if sys.platform != 'win32':
        raise RuntimeError(
            "Ebsilon functionality is only available on Windows platforms. "
            f"Current platform: {sys.platform}"
        )
    
    # Check Ebsilon installation
    is_available, message = check_ebsilon_installation()
    
    if is_available:
        print(f"✓ Ebsilon is properly installed and available at: {__ebsilon_path__}")
    else:
        print(f"✗ Ebsilon is not available: {message}")
        print("\nTo enable Ebsilon functionality:")
        print("1. Ensure Ebsilon Professional is installed on your system")
        print("2. Set the EBS environment variable to the Ebsilon installation path")
        print("   - Windows: setx EBS \"C:\\Path\\To\\Ebsilon\"")
        print("3. Restart your Python environment or IDE")


if __name__ == "__main__":
    # When run as a script, perform a full validation and output results
    validate_ebsilon_requirements()