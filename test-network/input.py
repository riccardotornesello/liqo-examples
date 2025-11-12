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

resource_schema = {
    "type": {"type": "string", "required": True},
    "cluster": {"type": "string", "required": True},
    "name": {"type": "string", "required": True},
    "namespace": {"type": "string", "required": True},
    "options": {"type": "dict", "required": False},
}

test_schema = {
    "name": {"type": "string", "required": True},
    "resources": {
        "type": "list",
        "required": False,
        "schema": {
            "type": "dict",
            "schema": resource_schema,
        },
    },
}

root_schema = {
    "clusters": {
        "type": "list",
        "required": True,
        "schema": {
            "type": "dict",
            "schema": cluster_schema,
        },
    },
    "tests": {
        "type": "list",
        "required": False,
        "schema": {
            "type": "dict",
            "schema": test_schema,
        },
    },
}


def parse_yaml(file_path):
    v = Validator(root_schema)

    with open(file_path, "r") as f:
        data = yaml.safe_load(f)

    if v.validate(data):
        return data

    else:
        raise ValueError(f"YAML validation error: {v.errors}")
