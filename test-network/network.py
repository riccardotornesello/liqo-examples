import json
from kubernetes import client, config


def get_remapped_cidr(kubeconfig_path, namespace, cr_name):
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

    CR_GROUP = "ipam.liqo.io"
    CR_VERSION = "v1alpha1"
    CR_PLURAL = "networks"

    # Load the kubeconfig file to configure the client
    config.load_kube_config(config_file=kubeconfig_path)

    # Create an instance of the API to interact with custom objects
    api_instance = client.CustomObjectsApi()

    # Retrieve the custom resource
    custom_resource = api_instance.get_namespaced_custom_object(
        group=CR_GROUP,
        version=CR_VERSION,
        namespace=namespace,
        plural=CR_PLURAL,
        name=cr_name,
    )

    # Extract and return the external Pod CIDR
    return custom_resource.get("status")["cidr"]


if __name__ == "__main__":
    KUBECONFIG_FILE = "../testbench/liqo_kubeconf_rome"
    NAMESPACE_NAME = "liqo-tenant-milan"
    CR_NAME = "milan-pod"

    spec = get_remapped_cidr(KUBECONFIG_FILE, NAMESPACE_NAME, CR_NAME)
    print(f"CIDR: {spec}")
