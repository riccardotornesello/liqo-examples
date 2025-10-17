#!/usr/bin/env python3

import os
from tabulate import tabulate
from kubernetes import client, config, stream

from pods import get_pod_ip
from services import get_service_ip
from network import get_remapped_cidr


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


def test_curl(kubeconfig, namespace, pod, target_ip):
    kube_client = client.CoreV1Api(api_client=config.new_client_from_config(kubeconfig))

    try:
        resp = stream.stream(
            kube_client.connect_get_namespaced_pod_exec,
            pod,
            namespace,
            command=[
                "curl",
                "-m",
                "1",
                "-s",
                "-o",
                "/dev/null",
                "-w",
                "%{http_code}",
                f"http://{target_ip}:80",
            ],
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False,
        )
        if resp == "200":
            # TODO: check if the hostname in the response body is correct
            return True
        else:
            return False
    except Exception as e:
        return False


clusters = {
    "consumer": ClusterConfig(
        "rome",
        "../testbench/liqo_kubeconf_rome",
        ["consumer-local", "offloaded"],
        ["po3"],
    ),
    "provider": ClusterConfig(
        "milan",
        "../testbench/liqo_kubeconf_milan",
        ["offloaded-rome", "provider-local"],
    ),
}

remapped_cidrs = {
    "consumer": get_remapped_cidr(
        clusters["consumer"].kubeconfig,
        f"liqo-tenant-{clusters['provider'].name}",
        f"{clusters['provider'].name}-pod",
    ),
    "provider": get_remapped_cidr(
        clusters["provider"].kubeconfig,
        f"liqo-tenant-{clusters['consumer'].name}",
        f"{clusters['consumer'].name}-pod",
    ),
}

sources = [
    {
        "name": p,
        "namespace": ns,
        "cluster": "consumer",
        "ip": clusters["consumer"].pod_ips[p],
    }
    for ns in clusters["consumer"].pods
    for p in clusters["consumer"].pods[ns]
    if p not in clusters["consumer"].offloaded_pods
] + [
    {
        "name": p,
        "namespace": ns,
        "cluster": "provider",
        "ip": clusters["provider"].pod_ips[p],
    }
    for ns in clusters["provider"].pods
    for p in clusters["provider"].pods[ns]
    if p not in clusters["provider"].offloaded_pods
]

destinations = (
    sources
    + [
        {
            "name": s,
            "namespace": ns,
            "cluster": "consumer",
            "ip": clusters["consumer"].service_ips[s],
        }
        for ns in clusters["consumer"].services
        for s in clusters["consumer"].services[ns]
    ]
    + [
        {
            "name": s,
            "namespace": ns,
            "cluster": "provider",
            "ip": clusters["provider"].service_ips[s],
        }
        for ns in clusters["provider"].services
        for s in clusters["provider"].services[ns]
    ]
)

print(sources)
print(destinations)

# TODO: parallelize
results = {}

for source in sources:
    results[source["name"]] = []

    for destination in destinations:
        if source["name"] == destination["name"]:
            results[source["name"]].append(None)
            continue

        target_ip = destination["ip"]
        if source["cluster"] != destination["cluster"]:
            # TODO: handle remapped CIDR other than /16
            target_ip = target_ip.split(".")
            target_remap_cidr = remapped_cidrs[destination["cluster"]].split(".")
            target_ip[0] = target_remap_cidr[0]
            target_ip[1] = target_remap_cidr[1]
            target_ip = ".".join(target_ip)

        print(
            f"Testing connectivity from pod {source['name']} ({source['ip']}) in cluster {source['cluster']} to {destination['name']} ({destination['ip']}) in cluster {destination['cluster']} via IP {target_ip}"
        )
        if test_curl(
            clusters[source["cluster"]].kubeconfig,
            source["namespace"],
            source["name"],
            target_ip,
        ):
            results[source["name"]].append(True)
            print("  \x1b[32mSUCCESS\x1b[0m")
        else:
            results[source["name"]].append(False)
            print("  \x1b[31mFAILURE\x1b[0m")

print(results)


def format_header_color(destination):
    destination_name = destination["name"]
    destination_cluster = destination["cluster"]

    color = "30"
    if destination_name.startswith("p"):
        if destination_cluster == "consumer":
            color = "43"
        else:
            color = "44"
    elif destination_name.startswith("s"):
        if destination_cluster == "consumer":
            color = "45"
        else:
            color = "46"

    return f"\x1b[{color}m {destination_name} \x1b[0m"


rows = [
    [format_header_color(source)]
    + [
        (
            "\x1b[42m  Y  \x1b[0m"
            if result == True
            else "\x1b[41m  N  \x1b[0m" if result == False else ""
        )
        for result in results[source["name"]]
    ]
    for source in sources
]


header = ["source pod"] + [format_header_color(dest) for dest in destinations]
print(tabulate(rows, headers=header))
