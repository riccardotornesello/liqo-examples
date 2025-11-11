import yaml

from cerberus import Validator


namespace_schema = {
    "name": {"type": "string", "required": True},
}

cluster_schema = {
    "name": {"type": "string", "required": True},
    "color": {"type": "string", "required": False},
    "kubeconfig_location": {"type": "string", "required": True},
    "namespaces": {
        "type": "list",
        "required": True,
        "schema": {
            "type": "dict",
            "schema": namespace_schema,
        },
    },
}

root_schema = {
    "clusters": {
        "type": "list",
        "required": True,
        "minlength": 2,
        "maxlength": 2,
        "schema": {
            "type": "dict",
            "schema": cluster_schema,
        },
    }
}


def parse_yaml(file_path):
    v = Validator(root_schema)

    with open(file_path, "r") as f:
        data = yaml.safe_load(f)

    if v.validate(data):
        return data

    else:
        raise ValueError(f"YAML validation error: {v.errors}")
