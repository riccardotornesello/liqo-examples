from typing import List

from config import validate_config_file, ClusterConfig, RuntimeEnum
from clusters.base import Cluster
from clusters.k3d import K3d


def parse(cluster_configs: List[ClusterConfig]) -> List[Cluster]:
    clusters: List[Cluster] = []

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

        clusters.append(cluster)

    return clusters


def main() -> None:
    cfg = validate_config_file("examples/base.yaml")
    if cfg is None:
        exit(1)

    clusters = parse(cfg.clusters)

    for cluster in clusters:
        print(f"Creating cluster: {cluster.name}")
        cluster.create()
        print(f"Cluster {cluster.name} created successfully.")


if __name__ == "__main__":
    main()
