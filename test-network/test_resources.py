from resources import NetworkPolicyResource, FirewallConfigurationResource
from clusters import clusters

# This policy successfully prevents the offloaded pods from pinging pods in other namespaces on the provider.
# However, it also blocks the offloaded pods from reaching the consumer's cluster.
EGRESS_NETWORK_POLICY = NetworkPolicyResource(
    body_location="resources/egress_network_policy.yaml",
    kubeconfig_path=clusters["provider"].kubeconfig,
    name="deny-egress-to-other-namespaces",
    namespace="offloaded-rome",
)

# NOTE: this policy does not work because the nftables see that the traffic is trying to reach the node's IP, not the pod's IP
GATEWAY_NETWORK_POLICY = NetworkPolicyResource(
    body_location="resources/gateway_network_policy.yaml",
    kubeconfig_path=clusters["provider"].kubeconfig,
    name="deny-egress-from-gateway",
    namespace="offloaded-rome",
)

TUNNEL_FIREWALL_RULE = FirewallConfigurationResource(
    kubeconfig_path=clusters["provider"].kubeconfig,
    name="restrict-tunnel-traffic",
    namespace="liqo-tenant-rome",
)
