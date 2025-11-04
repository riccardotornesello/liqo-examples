from resources import FirewallConfigurationResource


# TODO: update the FirewallConfiguration API to attach a chain to a specific interface
# TODO: update the FirewallConfiguration API to match established connections (?)
# TODO: update the FirewallConfiguration API to match multiple IPs/CIDRs in a single rule


class TunnelFirewallRuleResource(FirewallConfigurationResource):
    allowed_destination_ips: list[str]

    def __init__(
        self,
        kubeconfig_path: str,
        namespace: str,
        name: str,
        allowed_destination_ips: list[str],
    ):
        super().__init__(
            kubeconfig_path=kubeconfig_path,
            namespace=namespace,
            name=name,
        )
        self.allowed_destination_ips = allowed_destination_ips

    def _get_body_content(self) -> dict:
        accept_rules = [
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
                            "value": ip,
                        },
                        "op": "eq",
                    },
                ],
            }
            for ip in self.allowed_destination_ips
        ]

        return {
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
                    "name": "tunnel-firewall-table",
                    "chains": [
                        {
                            "hook": "forward",
                            "name": "tunnel-firewall-chain",
                            "policy": "accept",
                            "priority": 99,
                            "type": "filter",
                            "rules": {
                                "filterRules": [
                                    *accept_rules,
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
