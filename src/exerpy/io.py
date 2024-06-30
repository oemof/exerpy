import json
from exerpy.components import component_registry


def load_network_from_json(json_path):
    with open(json_path, "r") as f:
        data = json.load(f)

    components = _construct_components(data["components"])


def _construct_components(component_data):
    components = {}
    for component_class, components in component_data.items():
        for component, component_information in components.items():
            kwargs = component_information
            kwargs["label"] = component
            components[component] = component_registry.items()[component_class](**kwargs)

    return components
