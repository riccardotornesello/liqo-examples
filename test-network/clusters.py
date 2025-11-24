import os

from utils.kubernetes.nodes import Node, get_nodes
from utils.kubernetes.pods import Pod, get_pods, get_local_offloaded_pods
from utils.kubernetes.services import Service, get_services
from utils.kubernetes.remapped_cidrs import get_remapped_cidrs


class Cluster:
    """
    Represents a Kubernetes cluster with methods to retrieve pod and service information.

    Attributes:
        name (str): The name of the cluster.
        color (str): The color code associated with the cluster.
        kubeconfig_location (str): Path to the kubeconfig file for cluster access.
        namespaces (list[str]): List of namespaces to monitor in the cluster.
        nodes (list[Node]): List of nodes in the cluster.
        pods (dict[str, list[Pod]]): Dictionary mapping namespace to list of pods. Only includes non-virtual-node pods.
        services (dict[str, list[Service]]): Dictionary mapping namespace to list of services.
        remapped_cidrs (dict[str, str]): Dictionary mapping tenant names to their external Pod CIDRs.
        local_offloaded_pods (dict[str, list[Pod]]): Dictionary mapping origin cluster names to their offloaded pods.
    """

    name: str
    color: str
    kubeconfig_location: str

    namespaces: list[str]

    nodes: list[Node]
    pods: dict[str, list[Pod]]
    services: dict[str, list[Service]]
    remapped_cidrs: dict[str, str]
    local_offloaded_pods: dict[str, list[Pod]]

    def __init__(
        self,
        name: str,
        kubeconfig_location: str,
        namespaces: list[str],
        color: str = "44",
    ):
        """
        Initializes a Cluster instance and retrieves initial pod and service information.

        Args:
            name (str): The name of the cluster.
            kubeconfig_location (str): Path to the kubeconfig file.
            namespaces (list[str]): List of namespaces to monitor.
            color (str, optional): Color code for display purposes. Defaults to "44".

        Raises:
            FileNotFoundError: If the kubeconfig file does not exist.
        """
        if not os.path.exists(kubeconfig_location):
            raise FileNotFoundError(
                f"Kubeconfig file '{kubeconfig_location}' not found."
            )

        self.name = name
        self.color = color
        self.kubeconfig_location = kubeconfig_location

        self.namespaces = namespaces

        self.nodes = get_nodes(self.kubeconfig_location)

        virtual_nodes = [
            node.name
            for node in self.nodes
            if node.labels.get("liqo.io/type") == "virtual-node"
        ]
        self.pods = {
            ns: get_pods(
                self.kubeconfig_location, namespace=ns, excluded_nodes=virtual_nodes
            )
            for ns in self.namespaces
        }

        self.services = {
            ns: get_services(self.kubeconfig_location, namespace=ns)
            for ns in self.namespaces
        }

        self.local_offloaded_pods = get_local_offloaded_pods(self.kubeconfig_location)

        self.remapped_cidrs = get_remapped_cidrs(self.kubeconfig_location)


def load_clusters_from_config(config_data: list) -> list[Cluster]:
    """
    Loads cluster configurations from the provided data and initializes Cluster instances.

    Args:
        config_data (dict): Configuration data containing cluster information.

    Returns:
        list[Cluster]: List of initialized Cluster instances.
    """
    clusters = []

    for cluster_cfg in config_data:
        cluster = Cluster(
            name=cluster_cfg["name"],
            kubeconfig_location=cluster_cfg["kubeconfig_location"],
            namespaces=[ns_cfg["name"] for ns_cfg in cluster_cfg.get("namespaces", [])],
            color=cluster_cfg.get("color"),
        )
        clusters.append(cluster)

    return clusters
