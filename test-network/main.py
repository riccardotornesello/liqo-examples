#!/usr/bin/env python3

from time import sleep

from network import get_remapped_cidr
from tests import run_tests, TestManager
from output import print_results
from test_resources import EGRESS_NETWORK_POLICY, GATEWAY_NETWORK_POLICY
from resources import NetworkPolicyResource
from clusters import clusters


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


# Cleanup previous resources
for resource in [EGRESS_NETWORK_POLICY, GATEWAY_NETWORK_POLICY]:
    resource.delete()
sleep(1)

tests = [
    ("Default allow all egress", []),
    ("Deny offloaded egress", [EGRESS_NETWORK_POLICY]),
    # ("Block gateway traffic", [GATEWAY_NETWORK_POLICY]),
]

for test_name, test_resources in tests:
    with TestManager(test_name, test_resources):
        results = run_tests(sources, destinations, clusters, remapped_cidrs)
        print_results(results, sources, destinations)
