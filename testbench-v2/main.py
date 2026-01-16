import logging
import subprocess
import sys
from typing import List

from config import validate_config_file, ClusterConfig, RuntimeEnum
from clusters.base import Cluster
from clusters.k3d import K3d
from tools.liqo import LiqoTool
from logs import setup_logging, log_info, log_success, log_error


def create_docker_network(network_name: str) -> None:
    """Create a Docker network for the testbench clusters."""
    # Check if the Docker network already exists
    exists = (
        subprocess.run(
            ["docker", "network", "inspect", network_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )

    if exists:
        log_info(f"Docker network '{network_name}' already exists. Skipping.")
        return

    # If not, create it
    log_info(f"Creating Docker network: {network_name}")
    try:
        subprocess.run(
            ["docker", "network", "create", network_name],
            check=True,
            capture_output=True,
            text=True,
        )
        log_success(f"Docker network '{network_name}' created successfully")
    except subprocess.CalledProcessError as e:
        log_error(f"Failed to create Docker network: {e.stderr}")
        raise e


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
    """Main entry point for the testbench application."""
    # Initialize logging system
    try:
        setup_logging()
    except Exception as e:
        # Fallback to basic logging with similar format if setup fails
        print(f"Warning: Failed to setup logging: {e}", file=sys.stderr)
        logging.basicConfig(
            level=logging.INFO,
            format="%(levelname)s\t%(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),
            ],
        )
    
    # Create Docker network
    create_docker_network("testbench-net")

    # Fetch configuration
    cfg = validate_config_file("examples/base.yaml")
    if cfg is None:
        exit(1)

    # Create clusters
    clusters = parse(cfg.clusters)
    for cluster in clusters:
        log_info(f"Creating cluster: {cluster.name}")
        cluster.create()
        log_success(f"Cluster '{cluster.name}' created successfully")

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
        log_info(f"Installing tool: {tool.__class__.__name__}")
        tool.install()
        log_success(f"Tool '{tool.__class__.__name__}' installed successfully")


if __name__ == "__main__":
    main()
