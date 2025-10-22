#!/usr/bin/env python3

from time import sleep

from network import get_remapped_cidr
from tests import run_tests, TestManager
from output import print_results
from test_resources import (
    EGRESS_NETWORK_POLICY,
    GATEWAY_NETWORK_POLICY,
    TUNNEL_FIREWALL_RULE,
)
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
for resource in [
    EGRESS_NETWORK_POLICY,
    GATEWAY_NETWORK_POLICY,
    TUNNEL_FIREWALL_RULE,
]:
    resource.delete()
sleep(1)

# Generate dynamic test resources if needed
# TODO: update the API to attach a chain to a specific interface
# TODO: update the API to match established connections
# TODO: update the API to match multiple IPs/CIDRs in a single rule
TUNNEL_FIREWALL_RULE.set_body(
    {
        "apiVersion": "networking.liqo.io/v1beta1",
        "kind": "FirewallConfiguration",
        "metadata": {
            "labels": {
                "liqo.io/managed": "true",
                "networking.liqo.io/firewall-category": "gateway",
                "networking.liqo.io/firewall-subcategory": "fabric",
            }
        },
        "spec": {
            "table": {
                "family": "IPV4",
                "name": "test-table",
                "chains": [
                    {
                        "hook": "forward",
                        "name": "test-chain",
                        "policy": "accept",
                        "priority": 99,
                        "type": "filter",
                        "rules": {
                            "filterRules": [
                                {
                                    "action": "accept",
                                    "match": [
                                        {
                                            "dev": {
                                                "position": "in",
                                                "value": "liqo-tunnel",
                                            },
                                            "op": "eq",
                                        },
                                        {
                                            "ip": {
                                                "position": "dst",
                                                "value": clusters["provider"].pod_ips[
                                                    "po3"
                                                ],
                                            },
                                            "op": "eq",
                                        },
                                    ],
                                },
                                {
                                    "action": "accept",
                                    "match": [
                                        {
                                            "dev": {
                                                "position": "in",
                                                "value": "liqo-tunnel",
                                            },
                                            "op": "eq",
                                        },
                                        {
                                            "ip": {
                                                "position": "dst",
                                                "value": clusters["provider"].pod_ips[
                                                    "po4"
                                                ],
                                            },
                                            "op": "eq",
                                        },
                                    ],
                                },
                                {
                                    "action": "drop",
                                    "match": [
                                        {
                                            "dev": {
                                                "position": "in",
                                                "value": "liqo-tunnel",
                                            },
                                            "op": "eq",
                                        },
                                    ],
                                },
                            ]
                        },
                    }
                ],
            }
        },
    }
)


# Run tests
tests = [
    ("Default allow all egress", []),
    # ("Deny offloaded egress", [EGRESS_NETWORK_POLICY]),
    # ("Block gateway traffic", [GATEWAY_NETWORK_POLICY]),
    # ("Provider protection", [EGRESS_NETWORK_POLICY, TUNNEL_FIREWALL_RULE]),
]

for test_name, test_resources in tests:
    with TestManager(test_name, test_resources):
        results = run_tests(sources, destinations, clusters, remapped_cidrs)
        print_results(results, sources, destinations)
