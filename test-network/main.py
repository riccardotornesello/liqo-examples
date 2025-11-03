#!/usr/bin/env python3

from time import sleep

from network import get_remapped_cidr
from tests import run_tests, TestManager, TestEntity
from output import print_results
from clusters import clusters
from test_resources.tunnel_firewall_rule import TunnelFirewallRuleResource
from test_resources.egress_network_policy import EgressNetworkPolicyResource
from test_resources.gateway_network_policy import GatewayNetworkPolicyResource

######################################################
# GENERATE TEST ENTITIES
######################################################

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

pods = [
    TestEntity(
        name=p,
        namespace=ns,
        cluster_name="consumer",
        type="pod",
        ip=clusters["consumer"].pod_ips[p],
        test_suite=["ping", "curl"],
        color="43",
    )
    for ns in clusters["consumer"].pods
    for p in clusters["consumer"].pods[ns]
    if p not in clusters["consumer"].offloaded_pods
] + [
    TestEntity(
        name=p,
        namespace=ns,
        cluster_name="provider",
        type="pod",
        ip=clusters["provider"].pod_ips[p],
        test_suite=["ping", "curl"],
        color="44",
    )
    for ns in clusters["provider"].pods
    for p in clusters["provider"].pods[ns]
    if p not in clusters["provider"].offloaded_pods
]

services = [
    TestEntity(
        name=s,
        namespace=ns,
        cluster_name="consumer",
        type="service",
        ip=clusters["consumer"].service_ips[s],
        test_suite=["curl"],
        color="45",
    )
    for ns in clusters["consumer"].services
    for s in clusters["consumer"].services[ns]
] + [
    TestEntity(
        name=s,
        namespace=ns,
        cluster_name="provider",
        type="service",
        ip=clusters["provider"].service_ips[s],
        test_suite=["curl"],
        color="46",
    )
    for ns in clusters["provider"].services
    for s in clusters["provider"].services[ns]
]

internet = TestEntity(
    name="internet",
    namespace="",
    type="external",
    ip="8.8.8.8",
    test_suite=["ping"],
)

sources = pods
destinations = pods + services + [internet]


######################################################
# GENERATE TEST RESOURCES
######################################################

test_resources = {
    "TUNNEL_FIREWALL_RULE": TunnelFirewallRuleResource(
        kubeconfig_path=clusters["provider"].kubeconfig,
        name="restrict-tunnel-traffic",
        namespace="liqo-tenant-rome",
        allowed_destination_ips=[
            clusters["provider"].pod_ips["po3"],
            clusters["provider"].pod_ips["po4"],
        ],
    ),
    "EGRESS_NETWORK_POLICY": EgressNetworkPolicyResource(
        kubeconfig_path=clusters["provider"].kubeconfig,
        name="deny-egress-to-other-namespaces",
        namespace="offloaded-rome",
        allowed_cidrs=["10.71.0.0/16"],  # TODO: get from remapped
    ),
    "GATEWAY_NETWORK_POLICY": GatewayNetworkPolicyResource(
        kubeconfig_path=clusters["provider"].kubeconfig,
        name="deny-egress-from-gateway",
        namespace="offloaded-rome",
        remote_cluster_id="rome",
    ),
}

# Cleanup previous resources
for resource in test_resources.values():
    resource.delete()
sleep(1)

######################################################
# RUN TESTS
######################################################

tests_suites = [
    # ("Default allow all egress", []),
    # ("Deny offloaded egress", [EGRESS_NETWORK_POLICY]),
    # ("Block gateway traffic", [GATEWAY_NETWORK_POLICY]),
    (
        "Provider protection",
        [
            test_resources["EGRESS_NETWORK_POLICY"],
            test_resources["TUNNEL_FIREWALL_RULE"],
        ],
    ),
]

for test_name, test_resources in tests_suites:
    with TestManager(test_name, test_resources):
        results = run_tests(sources, destinations, clusters, remapped_cidrs)
        print_results(results, sources, destinations)
