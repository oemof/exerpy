from exerpy.parser.from_tespy.tespy_config import EXERPY_TESPY_MAPPINGS
from exerpy.components.component import component_registry

def test_tespy_component_mapping_targets_in_exerpy_components():
    """Test if all mapping targets for tespy are valid exerpy components"""
    for component in set(EXERPY_TESPY_MAPPINGS.values()):
        assert component in component_registry.items.keys()
