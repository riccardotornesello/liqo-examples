import os
from kubernetes import client, config

from network import get_pod_ip, get_service_ip


class Cluster:
    """
    Represents a Kubernetes cluster with methods to retrieve pod and service information.

    Attributes:
        name (str): The name of the cluster.
        kubeconfig (str): Path to the kubeconfig file for cluster access.
        namespaces (list[str]): List of namespaces to monitor in the cluster.
        offloaded_pods (list[str]): List of pod names that are offloaded to another cluster.
        pods (dict): Dictionary mapping namespace to list of pod names.
        pod_ips (dict): Dictionary mapping pod names to their IP addresses.
        services (dict): Dictionary mapping namespace to list of service names.
        service_ips (dict): Dictionary mapping service names to their cluster IPs.
    """

    def __init__(
        self,
        name: str,
        kubeconfig: str,
        namespaces: list[str],
        offloaded_pods: list[str] = None,
    ):
        """
        Initializes a Cluster instance and retrieves initial pod and service information.

        Args:
            name (str): The name of the cluster.
            kubeconfig (str): Path to the kubeconfig file.
            namespaces (list[str]): List of namespaces to monitor.
            offloaded_pods (list[str], optional): List of offloaded pod names. Defaults to None.

        Raises:
            FileNotFoundError: If the kubeconfig file does not exist.
        """
        self.name = name
        self.kubeconfig = kubeconfig
        self.namespaces = namespaces
        self.offloaded_pods = offloaded_pods if offloaded_pods is not None else []

        if not os.path.exists(kubeconfig):
            raise FileNotFoundError(f"Kubeconfig file '{kubeconfig}' not found.")

        self.refresh_pods()
        self.refresh_services()

    def refresh_pods(self) -> tuple[dict[str, list[str]], dict[str, str]]:
        """
        Refreshes the list of pods and their IP addresses from the cluster.

        Queries all configured namespaces and retrieves pod names and IPs.

        Returns:
            tuple[dict[str, list[str]], dict[str, str]]: A tuple containing:
                - Dictionary mapping namespace to list of pod names
                - Dictionary mapping pod names to their IP addresses
        """
        self.pods = {}
        self.pod_ips = {}

        for ns in self.namespaces:
            pod_list = client.CoreV1Api(
                api_client=config.new_client_from_config(self.kubeconfig)
            ).list_namespaced_pod(ns)

            self.pods[ns] = [pod.metadata.name for pod in pod_list.items]
            for pod in self.pods[ns]:
                self.pod_ips[pod] = get_pod_ip(self.kubeconfig, ns, pod)

        return self.pods, self.pod_ips

    def refresh_services(self) -> tuple[dict[str, list[str]], dict[str, str]]:
        """
        Refreshes the list of services and their cluster IPs from the cluster.

        Queries all configured namespaces and retrieves service names and cluster IPs.

        Returns:
            tuple[dict[str, list[str]], dict[str, str]]: A tuple containing:
                - Dictionary mapping namespace to list of service names
                - Dictionary mapping service names to their cluster IPs
        """
        self.services = {}
        self.service_ips = {}

        for ns in self.namespaces:
            svc_list = client.CoreV1Api(
                api_client=config.new_client_from_config(self.kubeconfig)
            ).list_namespaced_service(ns)

            self.services[ns] = [svc.metadata.name for svc in svc_list.items]
            for svc in self.services[ns]:
                self.service_ips[svc] = get_service_ip(self.kubeconfig, ns, svc)

        return self.services, self.service_ips


clusters = {
    "consumer": Cluster(
        "rome",
        "../testbench/liqo_kubeconf_rome",
        ["consumer-local", "offloaded"],
        ["po3", "po4"],
    ),
    "provider": Cluster(
        "milan",
        "../testbench/liqo_kubeconf_milan",
        ["offloaded-rome", "provider-local"],
    ),
}
