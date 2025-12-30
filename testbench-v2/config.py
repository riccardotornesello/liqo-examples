import yaml
import os
from typing import List, Optional, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationError


class CommonConfig(BaseModel):
    """
    Base model defining fields shared between the 'default' section
    and individual 'clusters'.
    """

    runtime: str = "k3d"  # TODO: enum
    cni: str = "flannel"  # TODO: enum
    workers: int = 1
    cache: bool = False
    liqo: bool = False

    resources: List[str] = Field(default_factory=list)

    @field_validator("resources")
    @classmethod
    def check_resources_exist(cls, v):
        """Validates that every path in the resources list exists on disk."""
        for path in v:
            if not os.path.exists(path):
                raise ValueError(f"Path does not exist: '{path}'")
        return v


class ClusterConfig(CommonConfig):
    """
    Extends CommonConfig with cluster-specific fields.
    """

    name: str
    peer: List[str] = Field(default_factory=list)


class RootConfig(BaseModel):
    default: Optional[CommonConfig] = Field(default_factory=CommonConfig)
    clusters: List[ClusterConfig]

    @model_validator(mode="before")
    @classmethod
    def merge_defaults_into_clusters(cls, data):
        """
        PRE-VALIDATION HOOK.
        Merges values from the 'default' section into each cluster entry
        if the cluster doesn't specify them.
        """
        if not isinstance(data, dict):
            return data  # Let Pydantic handle the type error

        defaults = data.get("default", {})
        clusters = data.get("clusters", [])

        if not isinstance(clusters, list):
            return data  # Let Pydantic handle the type error

        # We modify the raw dictionary data before Pydantic creates the objects.
        # This ensures that when ClusterConfig is instantiated, it has all the data.
        for cluster in clusters:
            if not isinstance(cluster, dict):
                continue

            # List of fields that can be inherited
            inheritable_fields = [
                "runtime",
                "workers",
                "cni",
                "cache",
                "liqo",
                "resources",
            ]

            for field in inheritable_fields:
                # Logic: If missing in cluster AND present in default -> Copy from default
                if field not in cluster and field in defaults:
                    cluster[field] = defaults[field]

        return data

    @model_validator(mode="after")
    def validate_global_logic(self):
        """
        POST-VALIDATION HOOK.
        Validates cross-cluster logic (Uniqueness, Peers).
        """
        cluster_names = set()

        # 1. Check Uniqueness
        for i, cluster in enumerate(self.clusters):
            if cluster.name in cluster_names:
                raise ValueError(
                    f"Duplicate cluster name found: '{cluster.name}' (at clusters.{i})."
                )
            cluster_names.add(cluster.name)

        # 2. Check Peers
        for i, cluster in enumerate(self.clusters):
            for p_idx, peer_name in enumerate(cluster.peer):
                if peer_name == cluster.name:
                    raise ValueError(
                        f"Cluster '{cluster.name}' (clusters.{i}) cannot be its own peer."
                    )
                if peer_name not in cluster_names:
                    raise ValueError(
                        f"Cluster '{cluster.name}' (clusters.{i}) refers to unknown peer '{peer_name}'."
                    )

        return self


def format_pydantic_error(err):
    """
    Formats Pydantic location tuple into a readable string.
    Example: ('clusters', 0, 'name') -> 'clusters.0.name'
    """
    loc_path = ".".join(str(x) for x in err["loc"])
    # Remove 'root.' prefix if present for cleaner output
    if loc_path.startswith("root."):
        loc_path = loc_path[5:]
    return f"{loc_path}: {err['msg']}"


def validate_config(file_path: str):
    """Loads and validates a YAML configuration file."""

    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return

    with open(file_path, "r") as f:
        try:
            raw_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"❌ YAML Syntax Error: {e}")
            return

    return validate_yaml(raw_data)


def validate_yaml(raw_data: Any):
    """Main function to run the validation."""

    if raw_data is None:
        print("❌ File is empty.")
        return

    try:
        # Trigger Validation
        RootConfig(**raw_data)
        print("✅ Validation Successful!")

    except ValidationError as e:
        print("❌ Validation Failed. Errors found:")
        for err in e.errors():
            print(f" - {format_pydantic_error(err)}")


if __name__ == "__main__":
    # Example usage
    # Generating a test file that exercises the inheritance and errors
    test_yaml = """
default:
  workers: 2            # Will be inherited by cluster-A
  resources: ["."]      # Will be inherited by cluster-A (exists)

clusters:
  - name: "cluster-A"
    runtime: "docker"
    cni: "calico"
    # workers inherited (2)
    # resources inherited (.)

  - name: "cluster-B"
    # runtime MISSING (error)
    cni: "flannel"
    workers: "not-a-number" # Type Error
    resources: ["/does/not/exist"] # Path Error
    peer: ["cluster-A", "cluster-X"] # Peer Error (cluster-X unknown)

  - name: "cluster-A" # Duplicate Name Error
    runtime: "containerd"
    cni: "cilium"
"""

    raw_data = yaml.safe_load(test_yaml)
    validate_yaml(raw_data)
