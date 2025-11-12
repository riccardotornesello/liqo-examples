from dataclasses import dataclass

from kubernetes import client, config


@dataclass
class Pod:
    name: str
    namespace: str
    ip: str


def get_pods(
    kubeconfig_path: str,
    namespace: str = None,
    excluded_nodes: list[str] = [],
) -> list[Pod]:
    """
    Retrieves the list of pods in the Kubernetes cluster.

    Args:
        kubeconfig_path (str): Path to the kubeconfig file.
        namespace (str, optional): Namespace to filter pods. If None, retrieves pods from all namespaces.
        excluded_nodes (list[str], optional): List of node names to exclude pods from.

    Returns:
        list[Pod]: List of Pod objects representing the pods in the cluster.
    """

    # Load Kubeconfig
    api_client = config.new_client_from_config(kubeconfig_path)

    # Create a CoreV1Api client
    v1 = client.CoreV1Api(api_client=api_client)

    pod_list = []

    # Get the list of all Pods
    if namespace:
        pods = v1.list_namespaced_pod(namespace)
    else:
        pods = v1.list_pod_for_all_namespaces()

    if not pods.items:
        return []

    # Iterate over each Pod
    for pod in pods.items:
        pod_name = pod.metadata.name
        pod_namespace = pod.metadata.namespace
        pod_ip = pod.status.pod_ip

        node_name = pod.spec.node_name

        if node_name in excluded_nodes:
            continue

        # Add the information to the list
        pod_list.append(
            Pod(
                name=pod_name,
                namespace=pod_namespace,
                ip=pod_ip,
            )
        )

    return pod_list


def get_local_offloaded_pods(
    kubeconfig_path: str,
) -> list[Pod]:
    """
    Retrieves the list of local offloaded pods in the Kubernetes cluster.
    Detects the origin cluster by checking the offloading.liqo.io/origin label

    Args:
        kubeconfig_path (str): Path to the kubeconfig file.

    Returns:
        dict[str, list[Pod]]: Offloaded pods mapped by their origin cluster.
    """
    # Load Kubeconfig
    api_client = config.new_client_from_config(kubeconfig_path)

    # Create a CoreV1Api client
    v1 = client.CoreV1Api(api_client=api_client)

    offloaded_pods: dict[str, list[Pod]] = {}

    # Get the list of all Pods
    pods = v1.list_pod_for_all_namespaces()

    if not pods.items:
        return offloaded_pods

    # Iterate over each Pod
    for pod in pods.items:
        pod_name = pod.metadata.name
        pod_namespace = pod.metadata.namespace
        pod_ip = pod.status.pod_ip

        labels = pod.metadata.labels or {}
        origin_cluster = labels.get("offloading.liqo.io/origin")

        if not origin_cluster:
            continue

        if origin_cluster not in offloaded_pods:
            offloaded_pods[origin_cluster] = []

        # Add the information to the list
        offloaded_pods[origin_cluster].append(
            Pod(
                name=pod_name,
                namespace=pod_namespace,
                ip=pod_ip,
            )
        )

    return offloaded_pods
