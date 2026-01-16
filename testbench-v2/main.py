from typing import List

from config import validate_config_file, ClusterConfig, RuntimeEnum
from clusters.base import Cluster
from clusters.k3d import K3d
from tools.liqo import LiqoTool


def parse(cluster_configs: List[ClusterConfig]) -> List[Cluster]:
    cls: List[Cluster] = []

    for cfg in cluster_configs:
        cluster: Cluster

        match cfg.runtime:
            case RuntimeEnum.k3d:
                cluster = K3d(
                    name=cfg.name,
                    nodes=cfg.nodes,
                    cluster_cidr="10.200.0.0/16",  # TODO make configurable
                    service_cidr="10.201.0.0/16",  # TODO make configurable
                    cni=cfg.cni,
                )
            case _:
                raise ValueError(f"Unsupported Runtime: {cfg.runtime}")

        cls.append(cluster)

    return cls


def main() -> None:
    # Fetch configuration
    cfg = validate_config_file("examples/base.yaml")
    if cfg is None:
        exit(1)

    # Create clusters
    clusters = parse(cfg.clusters)
    # for cluster in clusters:
    #     print(f"Creating cluster: {cluster.name}")
    #     cluster.create()
    #     print(f"Cluster {cluster.name} created successfully.")

    # Install tools
    tools = []
    if cfg.tools.liqo:
        tools.append(
            LiqoTool(
                config=cfg.tools.liqo,
                clusters={cluster.name: cluster for cluster in clusters},
            )
        )

    for tool in tools:
        print(f"Installing tool: {tool.__class__.__name__}")
        tool.install()
        print(f"Tool {tool.__class__.__name__} installed successfully.")


if __name__ == "__main__":
    main()
