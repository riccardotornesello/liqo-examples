from resources import NetworkPolicyResource

# This policy does not work because the nftables see that the traffic is trying to reach the node's IP, not the pod's IP


class GatewayNetworkPolicyResource(NetworkPolicyResource):
    remote_cluster_id: str

    def __init__(
        self,
        kubeconfig_path: str,
        namespace: str,
        name: str,
        remote_cluster_id: str,
    ):
        super().__init__(
            kubeconfig_path=kubeconfig_path,
            namespace=namespace,
            name=name,
        )
        self.remote_cluster_id = remote_cluster_id

    def _get_body_content(self) -> dict:
        return {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "spec": {
                "podSelector": {},
                "policyTypes": ["Egress"],
                "egress": [
                    {
                        "to": [
                            {
                                "namespaceSelector": {
                                    "matchLabels": {
                                        "liqo.io/remote-cluster-id": self.remote_cluster_id,
                                    }
                                }
                            }
                        ]
                    }
                ],
            },
        }
