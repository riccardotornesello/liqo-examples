from resources.liqo import NetworkResource


def get_remapped_cidrs(kubeconfig_path: str) -> dict[str, str]:
    """
    Connects to a Kubernetes cluster using the provided kubeconfig file,
    retrieves the remapped CIDRs from Custom Resources, and returns them.

    Args:
        kubeconfig_path (str): Path to the kubeconfig file.

    Returns:
        dict[str, str]: A dictionary mapping tenant names to their external Pod CIDRs.
    """

    network_resource = NetworkResource(
        kubeconfig_path=kubeconfig_path,
    )
    all_crs = network_resource.list()

    results = {}
    for cr in all_crs:
        metadata = cr.get("metadata", {})
        name = metadata.get("name")
        namespace = metadata.get("namespace")

        if not name or not namespace:
            continue

        # Filter by namespace 'liqo-tenant-*'
        if not namespace.startswith("liqo-tenant-"):
            continue

        # Filter by name '*-pod'
        if not name.endswith("-pod"):
            continue
        status = cr.get("status")
        if not status:
            continue

        cidr = status.get("cidr")
        if not cidr:
            continue

        tenant_name = name[:-4]  # Remove the suffix '-pod'
        results[tenant_name] = cidr

    return results
