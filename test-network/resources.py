from kubernetes import client, config
from kubernetes.client.rest import ApiException


EGRESS_NETWORK_POLICY = {
    "apiVersion": "networking.k8s.io/v1",
    "kind": "NetworkPolicy",
    "metadata": {
        "name": "deny-egress-to-other-namespaces",
        "namespace": "offloaded-rome",
    },
    "spec": {
        "podSelector": {},  # Apply to all pods in the namespace
        "policyTypes": ["Egress"],
        "egress": [
            {
                # Allow egress only to pods within the same namespace
                "to": [{"podSelector": {}}]
            },
            {
                # Allow egress only to remapped CIDRs
                "to": [
                    {
                        "ipBlock": {
                            "cidr": "10.71.0.0/16",  # TODO: make this configurable
                        }
                    }
                ]
            },
        ],
    },
}

GATEWAY_NETWORK_POLICY = {
    "apiVersion": "networking.k8s.io/v1",
    "kind": "NetworkPolicy",
    "metadata": {
        "name": "deny-egress-from-gateway",
        "namespace": "liqo-tenant-rome",
    },
    "spec": {
        "podSelector": {},  # Apply to all pods in the namespace
        "policyTypes": ["Egress"],
        "egress": [
            {
                # Allow egress only to owned namespaces
                "to": [
                    {
                        "namespaceSelector": {
                            "matchLabels": {"liqo.io/remote-cluster-id": "rome"}
                        }
                    }
                ]
            }
        ],
    },
}


def create_kubernetes_network_policy(
    body: dict,
    kubeconfig: str,
):
    api_instance = client.NetworkingV1Api(
        api_client=config.new_client_from_config(kubeconfig)
    )

    return api_instance.create_namespaced_network_policy(
        namespace=body["metadata"]["namespace"], body=body
    )


def delete_kubernetes_network_policy(
    body: dict,
    kubeconfig: str,
    exception_on_not_found: bool = False,
):
    name = body["metadata"]["name"]
    namespace = body["metadata"]["namespace"]

    api_instance = client.NetworkingV1Api(
        api_client=config.new_client_from_config(kubeconfig)
    )

    try:
        return api_instance.delete_namespaced_network_policy(
            name=name,
            namespace=namespace,
        )
    except ApiException as e:
        if e.status == 404 and not exception_on_not_found:
            print(
                f"NetworkPolicy '{name}' in namespace '{namespace}' not found. Skipping deletion."
            )
            return

        else:
            raise e
