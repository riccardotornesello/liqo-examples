from resources.liqo import FirewallConfigurationResource
from clusters import Cluster


class TunnelFirewallRuleResource(FirewallConfigurationResource):
    """
    Options:
        allowed_destination_ips (list[str]): List of allowed destination IPs.
        allowed_source_ips (list[str]): List of allowed source IPs.
        allow_to_offloaded_pods_from (str): Allow traffic to offloaded pods from specific clusters.
        allow_established (bool): Whether to allow established connections. Defaults to True.
    """

    def _get_body_content(self) -> dict:
        # Settings
        table_name = f"tunnel-firewall-table-{self.name}"

        clusters: list[Cluster] = self.options["clusters"]
        cluster: str = self.options["cluster"]

        allowed_destination_ips: list[str] = self.options.get(
            "allowed_destination_ips", []
        )
        allowed_source_ips: list[str] = self.options.get("allowed_source_ips", [])
        allow_to_offloaded_pods_from: str | None = self.options.get(
            "allow_to_offloaded_pods_from"
        )
        allow_established: bool = self.options.get("allow_established", True)

        # Add allowed IPs for offloaded pods
        if allow_to_offloaded_pods_from:
            for c in clusters:
                if c.name != cluster:
                    continue

                offloaded_pods = c.local_offloaded_pods.get(
                    allow_to_offloaded_pods_from, {}
                )
                for pod in offloaded_pods:
                    if pod.ip not in allowed_destination_ips:
                        allowed_destination_ips.append(pod.ip)

        # Rules
        accept_destination_rules = [
            {
                "action": "accept",
                "match": [
                    {
                        "ip": {
                            "position": "dst",
                            "value": ip,
                        },
                        "op": "eq",
                    },
                ],
            }
            for ip in allowed_destination_ips
        ]

        accept_source_rules = [
            {
                "action": "accept",
                "match": [
                    {
                        "ip": {
                            "position": "src",
                            "value": ip,
                        },
                        "op": "eq",
                    },
                ],
            }
            for ip in allowed_source_ips
        ]

        established_rule = {
            "action": "accept",
            "match": [
                {
                    "ctstate": {
                        "value": [
                            "established",
                            "related",
                        ],
                    },
                    "op": "eq",
                },
            ],
        }

        # Body
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
                    "name": table_name,
                    "chains": [
                        {
                            "hook": "postrouting",
                            "name": "tunnel-firewall-chain",
                            "policy": "drop",
                            "priority": 200,
                            "type": "filter",
                            "rules": {
                                "filterRules": [
                                    # Consider only traffic coming from the wireguard tunnel to the geneve tunnels
                                    {
                                        "action": "accept",
                                        "match": [
                                            {
                                                "dev": {
                                                    "position": "in",
                                                    "value": "liqo-tunnel",
                                                },
                                                "op": "neq",
                                            },
                                        ],
                                    },
                                    {
                                        "action": "accept",
                                        "match": [
                                            {
                                                "dev": {
                                                    "position": "out",
                                                    "value": "eth0",
                                                },
                                                "op": "eq",
                                            },
                                        ],
                                    },
                                    # Accept allowed rules
                                    *([established_rule] if allow_established else []),
                                    *accept_destination_rules,
                                    *accept_source_rules,
                                ]
                            },
                        }
                    ],
                }
            },
        }
