import os
from kubernetes import client, config

from pods import get_pod_ip
from services import get_service_ip


class ClusterConfig:
    def __init__(self, name, kubeconfig, namespaces, offloaded_pods=[]):
        self.name = name
        self.kubeconfig = kubeconfig
        self.namespaces = namespaces
        self.offloaded_pods = offloaded_pods

        if not os.path.exists(kubeconfig):
            raise FileNotFoundError(f"Kubeconfig file '{kubeconfig}' not found.")

        self.client = client.CoreV1Api(
            api_client=config.new_client_from_config(kubeconfig)
        )

        self.pods, self.pod_ips = self.get_pods()
        self.services, self.service_ips = self.get_services()

    def get_pods(self):
        pods = {}
        pod_ips = {}

        for ns in self.namespaces:
            pod_list = self.client.list_namespaced_pod(ns)
            pods[ns] = [pod.metadata.name for pod in pod_list.items]
            for pod in pods[ns]:
                pod_ips[pod] = get_pod_ip(self.client, ns, pod)

        return pods, pod_ips

    def get_services(self):
        services = {}
        service_ips = {}

        for ns in self.namespaces:
            svc_list = self.client.list_namespaced_service(ns)
            services[ns] = [svc.metadata.name for svc in svc_list.items]
            for svc in services[ns]:
                service_ips[svc] = get_service_ip(self.client, ns, svc)

        return services, service_ips
