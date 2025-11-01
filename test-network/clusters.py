import os
from kubernetes import client, config

from network import get_pod_ip, get_service_ip


class Cluster:
    def __init__(self, name, kubeconfig, namespaces, offloaded_pods=[]):
        self.name = name
        self.kubeconfig = kubeconfig
        self.namespaces = namespaces
        self.offloaded_pods = offloaded_pods

        if not os.path.exists(kubeconfig):
            raise FileNotFoundError(f"Kubeconfig file '{kubeconfig}' not found.")

        self.refresh_pods()
        self.refresh_services()

    def refresh_pods(self):
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

    def refresh_services(self):
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
