from .isolation_network_policy import IsolationNetworkPolicyResource
from .tunnel_firewall_rule import TunnelFirewallRuleResource

test_resources = {
    "isolation_network_policy": IsolationNetworkPolicyResource,
    "tunnel_firewall_rule": TunnelFirewallRuleResource,
}
