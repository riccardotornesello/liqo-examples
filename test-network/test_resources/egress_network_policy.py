from resources import NetworkPolicyResource

# This policy successfully prevents the offloaded pods from pinging pods in other namespaces on the provider.
# However, it also blocks the offloaded pods from reaching the consumer's cluster.


class EgressNetworkPolicyResource(NetworkPolicyResource):
    allowed_cidrs: list[str]

    def __init__(
        self,
        kubeconfig_path: str,
        namespace: str,
        name: str,
        allowed_cidrs: list[str],
    ):
        super().__init__(
            kubeconfig_path=kubeconfig_path,
            namespace=namespace,
            name=name,
        )
        self.allowed_cidrs = allowed_cidrs

    def _get_body_content(self) -> dict:
        allowed_cidr_rules = [
            {
                "to": [
                    {
                        "ipBlock": {
                            "cidr": cidr,
                        }
                    }
                ]
            }
            for cidr in self.allowed_cidrs
        ]

        return {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "spec": {
                "podSelector": {},
                "policyTypes": ["Egress"],
                "egress": [
                    {"to": [{"podSelector": {}}]},
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
                    *allowed_cidr_rules,
                ],
            },
        }
