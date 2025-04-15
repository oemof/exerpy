import functools
from typing import Any
from typing import Callable
from typing import TypeVar
from typing import cast

from exerpy.parser.from_ebsilon import __ebsilon_available__

# Type variable for the decorated function
F = TypeVar('F', bound=Callable[..., Any])

def require_ebsilon(func: F) -> F:
    """
    Decorator to ensure that Ebsilon functionality is available.
    
    Args:
        func: The function that requires Ebsilon functionality
        
    Returns:
        The wrapped function that checks for Ebsilon availability
        
    Raises:
        RuntimeError: If Ebsilon functionality is not available
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not __ebsilon_available__:
            error_msg = (
                "Ebsilon functionality is not available because the 'EBS' "
                "environment variable is not set or EbsOpen could not be imported. "
                "Please set the EBS environment variable to your Ebsilon installation path."
            )
            raise RuntimeError(error_msg)
        return func(*args, **kwargs)
    
    return cast(F, wrapper)


# Stub classes for when Ebsilon isn't available
class EpSubstanceStub:
    """Stub class for EpSubstance when Ebsilon is not available."""
    epSubstanceN2 = 0
    epSubstanceO2 = 1
    epSubstanceCO2 = 2
    epSubstanceH2O = 3
    epSubstanceAR = 4
    # Add other substance constants as needed with placeholder values
    
    @staticmethod
    def get_substance_name(substance_id: int) -> str:
        """Return placeholder substance name for the given ID."""
        return f"Substance_{substance_id}"


class EpFluidTypeStub:
    """Stub class for EpFluidType when Ebsilon is not available."""
    epFluidTypeNONE = 0
    epFluidTypeAir = 1
    epFluidTypeFluegas = 2
    epFluidTypeSteam = 3
    epFluidTypeWater = 4
    # Add other fluid type constants as needed


class EpSteamTableStub:
    """Stub class for EpSteamTable when Ebsilon is not available."""
    epSteamTableFromSuperiorModel = 0


class EpGasTableStub:
    """Stub class for EpGasTable when Ebsilon is not available."""
    epGasTableFromSuperiorModel = 0


class EpCalculationResultStatus2Stub:
    """Stub class for EpCalculationResultStatus2 when Ebsilon is not available."""
    epCalculationResultStatus2OK = 0
    epCalculationResultStatus2Warning = 1
    epCalculationResultStatus2Error = 2