#!/usr/bin/env python3

from time import sleep

from clusters import ClusterConfig
from network import get_remapped_cidr
from resources import (
    create_kubernetes_network_policy,
    delete_kubernetes_network_policy,
    EGRESS_NETWORK_POLICY,
    GATEWAY_NETWORK_POLICY,
)
from tests import run_tests
from output import print_results


clusters = {
    "consumer": ClusterConfig(
        "rome",
        "../testbench/liqo_kubeconf_rome",
        ["consumer-local", "offloaded"],
        ["po3", "po4"],
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
        "type": "pod",
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
        "type": "pod",
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
            "type": "service",
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
            "type": "service",
            "ip": clusters["provider"].service_ips[s],
        }
        for ns in clusters["provider"].services
        for s in clusters["provider"].services[ns]
    ]
)


class TestManager:
    def __init__(self, test_name, network_policies):
        self.test_name = test_name
        self.network_policies = network_policies

    def __enter__(self):
        print(f"========== Setting up test: {self.test_name} ==========")
        if self.network_policies:
            for policy in self.network_policies:
                create_kubernetes_network_policy(
                    policy,
                    clusters["provider"].kubeconfig,
                )
            sleep(1)

    def __exit__(self, exc_type, exc_value, traceback):
        print(f"========== Tearing down test: {self.test_name} ==========")
        if self.network_policies:
            for policy in self.network_policies:
                delete_kubernetes_network_policy(
                    policy,
                    clusters["provider"].kubeconfig,
                    exception_on_not_found=True,
                )
        sleep(1)


# Cleanup previous network policy if exists
for policy in [EGRESS_NETWORK_POLICY, GATEWAY_NETWORK_POLICY]:
    delete_kubernetes_network_policy(
        policy,
        clusters["provider"].kubeconfig,
        exception_on_not_found=False,
    )
sleep(1)

tests = [
    ("Default allow all egress", []),
    ("Deny all egress", [EGRESS_NETWORK_POLICY]),
    ("Block gateway traffic", [GATEWAY_NETWORK_POLICY]),
]

for test_name, network_policies in tests:
    with TestManager(test_name, network_policies):
        results = run_tests(sources, destinations, clusters, remapped_cidrs)
        print_results(results, sources, destinations)
