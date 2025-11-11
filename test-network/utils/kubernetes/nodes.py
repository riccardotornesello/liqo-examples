from dataclasses import dataclass

from kubernetes import client, config


@dataclass
class Node:
    name: str
    labels: dict[str, str]


def get_nodes(kubeconfig_path: str) -> list[Node]:
    """
    Retrieves the list of nodes in the Kubernetes cluster.

    Args:
        kubeconfig_path (str): Path to the kubeconfig file.

    Returns:
        list[Node]: List of Node objects representing the nodes in the cluster.
    """

    # Load Kubeconfig
    api_client = config.new_client_from_config(kubeconfig_path)

    # Create a CoreV1Api client
    v1 = client.CoreV1Api(api_client=api_client)

    node_list = []

    # Get the list of all Nodes
    nodes = v1.list_node()

    if not nodes.items:
        return []

    # Iterate over each Node
    for node in nodes.items:
        node_name = node.metadata.name

        # Labels are already in dictionary format
        # If there are no labels, node.metadata.labels is None
        node_labels = node.metadata.labels if node.metadata.labels else {}

        # Add the information to the list
        node_list.append(Node(name=node_name, labels=node_labels))

    return node_list
