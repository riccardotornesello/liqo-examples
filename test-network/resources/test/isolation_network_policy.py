from resources.kubernetes import NetworkPolicyResource
from clusters import Cluster


class IsolationNetworkPolicyResource(NetworkPolicyResource):
    """
    Options:
        allowed_cidrs (list[str]): List of allowed CIDR blocks.
        allowed_namespaces (list[str]): List of allowed namespaces.
        allowed_clusters (list[str]): List of allowed clusters.
    """

    def _get_body_content(self) -> dict:
        # Settings
        clusters: list[Cluster] = self.options["clusters"]
        cluster: str = self.options["cluster"]

        allowed_cidrs = self.options.get("allowed_cidrs", [])
        allowed_namespaces = self.options.get("allowed_namespaces", [])
        allowed_clusters = self.options.get("allowed_clusters", [])

        current_cluster = None
        for c in clusters:
            if c.name == cluster:
                current_cluster = c
                break
        if not current_cluster:
            raise ValueError(f"Cluster '{cluster}' not found in clusters list.")

        # Rules
        allowed_cidr_egress_rules = [
            {
                "to": [
                    {
                        "ipBlock": {
                            "cidr": cidr,
                        }
                    }
                ]
            }
            for cidr in allowed_cidrs
        ]
        allowed_cidr_ingress_rules = [
            {
                "from": [
                    {
                        "ipBlock": {
                            "cidr": cidr,
                        }
                    }
                ]
            }
            for cidr in allowed_cidrs
        ]

        allowed_namespaces_egress_rules = [
            {"to": [{"namespaceSelector": {"matchLabels": {"name": ns}}}]}
            for ns in allowed_namespaces
        ]
        allowed_namespaces_ingress_rules = [
            {"from": [{"namespaceSelector": {"matchLabels": {"name": ns}}}]}
            for ns in allowed_namespaces
        ]

        allowed_clusters_egress_rules = [
            {"to": [{"ipBlock": {"cidr": current_cluster.remapped_cidrs[c]}}]}
            for c in allowed_clusters
        ]
        allowed_clusters_ingress_rules = [
            {"from": [{"ipBlock": {"cidr": current_cluster.remapped_cidrs[c]}}]}
            for c in allowed_clusters
        ]

        # Body
        return {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "spec": {
                "podSelector": {},
                "policyTypes": ["Egress", "Ingress"],
                "egress": [
                    # Allow traffic to pods in the same namespace
                    {"to": [{"podSelector": {}}]},
                    # Allow traffic to pods in allowed namespaces
                    *allowed_namespaces_egress_rules,
                    # Allow traffic to allowed CIDRs
                    *allowed_cidr_egress_rules,
                    # Allow traffic to allowed clusters
                    *allowed_clusters_egress_rules,
                    # Block traffic to other private IP ranges
                    {
                        "to": [
                            {
                                "ipBlock": {
                                    "cidr": "0.0.0.0/0",
                                    "except": [
                                        "10.0.0.0/8",
                                        "192.168.0.0/16",
                                        "172.16.0.0/20",
                                    ],
                                }
                            }
                        ]
                    },
                ],
                "ingress": [
                    # Allow traffic from pods in the same namespace
                    {"from": [{"podSelector": {}}]},
                    # Allow traffic from pods in allowed namespaces
                    *allowed_namespaces_ingress_rules,
                    # Allow traffic from allowed CIDRs
                    *allowed_cidr_ingress_rules,
                    # Allow traffic from allowed clusters
                    *allowed_clusters_ingress_rules,
                ],
            },
        }
