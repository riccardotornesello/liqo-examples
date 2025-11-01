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


def get_pod_ip(kubeconfig_path: str, namespace: str, pod: str) -> str:
    """
    Retrieves the IP address of a specific pod.

    Args:
        kubeconfig_path (str): Path to the kubeconfig file.
        namespace (str): The namespace where the pod is located.
        pod (str): The name of the pod.

    Returns:
        str: The IP address of the pod.
    """
    kube_client = client.CoreV1Api(
        api_client=config.new_client_from_config(kubeconfig_path)
    )

    pod_obj = kube_client.read_namespaced_pod(pod, namespace)
    return pod_obj.status.pod_ip


def get_service_ip(kubeconfig_path: str, namespace: str, service: str) -> str:
    """
    Retrieves the cluster IP address of a specific service.

    Args:
        kubeconfig_path (str): Path to the kubeconfig file.
        namespace (str): The namespace where the service is located.
        service (str): The name of the service.

    Returns:
        str: The cluster IP address of the service.
    """
    kube_client = client.CoreV1Api(
        api_client=config.new_client_from_config(kubeconfig_path)
    )

    svc = kube_client.read_namespaced_service(service, namespace)
    return svc.spec.cluster_ip


def remap_ip(original_ip: str, remapped_cidr: str) -> str:
    """
    Remaps an IP address from the original CIDR to the remapped CIDR.

    This function takes an IP address and remaps it to a new CIDR block by:
    1. Converting the original IP to binary format
    2. Converting the remapped CIDR to binary format
    3. Replacing the network prefix of the original IP with the remapped CIDR prefix
    4. Converting the result back to IP format

    Args:
        original_ip (str): The original IP address to be remapped.
        remapped_cidr (str): The remapped CIDR block (e.g., "10.0.0.0/16").

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
    """
    Converts an IP address to its 32-bit binary representation.

    Args:
        ip (str): The IP address to convert.

    Returns:
        str: The binary representation of the IP address, zero-padded to 32 bits.
    """
    return bin(int(ip_address(ip)))[2:].zfill(32)


def bin_to_ip(bin_str: str) -> str:
    """
    Converts a binary string to an IP address.

    Args:
        bin_str (str): The binary string representation of an IP address.

    Returns:
        str: The IP address in standard dotted-decimal notation.
    """
    return str(ip_address(int(bin_str, 2)))


def cidr_to_bin(cidr: str) -> str:
    """
    Converts a CIDR network to its binary prefix representation.

    Args:
        cidr (str): The CIDR notation (e.g., "10.0.0.0/16").

    Returns:
        str: The binary representation of the network prefix.
    """
    network = ip_network(cidr, strict=False)
    return bin(int(network.network_address))[2:].zfill(32)[: network.prefixlen]
