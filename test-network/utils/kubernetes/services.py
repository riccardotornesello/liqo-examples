from dataclasses import dataclass

from kubernetes import client, config


@dataclass
class Service:
    name: str
    namespace: str
    cluster_ip: str


def get_services(kubeconfig_path: str, namespace: str = None) -> list[Service]:
    """
    Retrieves the list of services in the Kubernetes cluster.

    Args:
        kubeconfig_path (str): Path to the kubeconfig file.
        namespace (str, optional): Namespace to filter services. If None, retrieves services from all namespaces.

    Returns:
        list[Service]: List of Service objects representing the services in the cluster.
    """

    # Load Kubeconfig
    api_client = config.new_client_from_config(kubeconfig_path)

    # Create a CoreV1Api client
    v1 = client.CoreV1Api(api_client=api_client)

    service_list = []

    # Get the list of all Services
    if namespace:
        services = v1.list_namespaced_service(namespace)
    else:
        services = v1.list_service_for_all_namespaces()

    if not services.items:
        return []

    # Iterate over each Service
    for svc in services.items:
        svc_name = svc.metadata.name
        svc_namespace = svc.metadata.namespace
        svc_cluster_ip = svc.spec.cluster_ip

        # Add the information to the list
        service_list.append(
            Service(
                name=svc_name,
                namespace=svc_namespace,
                cluster_ip=svc_cluster_ip,
            )
        )

    return service_list
