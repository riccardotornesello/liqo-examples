import subprocess
from typing import Dict

from config import LiqoConfig
from tools.base import Tool
from clusters.k3d import K3d
from clusters.base import Cluster


class LiqoTool(Tool):
    config: LiqoConfig
    clusters: Dict[str, Cluster]

    def __init__(self, config: LiqoConfig, clusters: Dict[str, Cluster]) -> None:
        self.config = config
        self.clusters = clusters

    def install(self) -> None:
        for installation in self.config.installations:
            cluster = self.clusters[installation.cluster]

            if isinstance(cluster, K3d):
                self._install_in_cluster(
                    runtime="k3s",
                    cluster_id=cluster.name,
                    kubeconfig=cluster.get_kubeconfig_location(),
                    version=installation.version,
                    api_server_url=cluster.get_api_server_address(),
                    pod_cidr=cluster.cluster_cidr,
                    service_cidr=cluster.service_cidr,
                )
            else:
                raise ValueError(
                    f"Liqo installation is not supported for cluster: {cluster.name}"
                )

    def _install_in_cluster(
        self,
        runtime: str,
        cluster_id: str,
        kubeconfig: str,
        version: str,
        api_server_url: str | None = None,
        pod_cidr: str | None = None,
        service_cidr: str | None = None,
    ) -> None:
        print(f"Installing Liqo version {version}")

        repo_url = None
        version_hash = None
        if version is not None and version != "latest":
            (repo_url, version_hash) = version.split("@")

        command = [
            "liqoctl",
            "install",
            runtime,
        ]

        # Build installation command by adding parameters
        parameters = {
            "--cluster-id": cluster_id,
            "--pod-cidr": pod_cidr,
            "--service-cidr": service_cidr,
            "--kubeconfig": kubeconfig,
            "--api-server-url": api_server_url,
            "--repo-url": repo_url,
            "--version": version_hash,
        }

        for param, value in parameters.items():
            if value is not None:
                command.extend([param, value])

        # Execute installation command
        subprocess.run(command, check=True)
