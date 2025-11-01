from ipaddress import ip_address, ip_network

from kubernetes import client, config

from resources import NetworkResource


def get_remapped_cidr(kubeconfig_path: str, namespace: str, cr_name: str) -> str:
    """
    Connects to a Kubernetes cluster using the provided kubeconfig file,
    retrieves the remapped CIDR from a specific Custom Resource, and returns it.

    Args:
        kubeconfig_path (str): Path to the kubeconfig file.
        namespace (str): The namespace where the Custom Resource is located.
        cr_name (str): The name of the Custom Resource instance.

    Returns:
        str: The external Pod CIDR if found, None otherwise.
    """

    network_resource = NetworkResource(
        kubeconfig_path=kubeconfig_path,
        namespace=namespace,
        name=cr_name,
    )
    custom_resource = network_resource.get()

    # Extract and return the external Pod CIDR
    return custom_resource.get("status")["cidr"]


def get_pod_ip(kubeconfig_path: str, namespace, pod):
    kube_client = client.CoreV1Api(
        api_client=config.new_client_from_config(kubeconfig_path)
    )

    pod_obj = kube_client.read_namespaced_pod(pod, namespace)
    return pod_obj.status.pod_ip


def get_service_ip(kubeconfig_path: str, namespace, service):
    kube_client = client.CoreV1Api(
        api_client=config.new_client_from_config(kubeconfig_path)
    )

    svc = kube_client.read_namespaced_service(service, namespace)
    return svc.spec.cluster_ip


def remap_ip(original_ip: str, remapped_cidr: str):
    """
    Remaps an IP address from the original CIDR to the remapped CIDR.

    Args:
        original_ip (str): The original IP address to be remapped.
        remapped_cidr (str): The remapped CIDR block.

    Returns:
        str: The remapped IP address.
    """
    # Convert IP and CIDR to binary format
    original_ip_bin = ip_to_bin(original_ip)
    remapped_cidr_bin = cidr_to_bin(remapped_cidr)

    # Calculate the remapped IP address
    remapped_ip_bin = remapped_cidr_bin + original_ip_bin[len(remapped_cidr_bin) :]

    return bin_to_ip(remapped_ip_bin)


def ip_to_bin(ip: str) -> str:
    return bin(int(ip_address(ip)))[2:].zfill(32)


def bin_to_ip(bin_str: str) -> str:
    return str(ip_address(int(bin_str, 2)))


def cidr_to_bin(cidr: str) -> str:
    network = ip_network(cidr, strict=False)
    return bin(int(network.network_address))[2:].zfill(32)[: network.prefixlen]
