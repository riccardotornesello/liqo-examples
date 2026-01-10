from kubernetes import client, utils, config


def create_calico_config(cluster_cidr: str) -> list[dict]:
    return [
        {
            "apiVersion": "operator.tigera.io/v1",
            "kind": "Installation",
            "metadata": {"name": "default"},
            "spec": {
                "calicoNetwork": {
                    "nodeAddressAutodetectionV4": {"skipInterface": "liqo.*"},
                    "ipPools": [
                        {
                            "name": "default-ipv4-ippool",
                            "blockSize": 26,
                            "cidr": cluster_cidr,
                            "encapsulation": "VXLAN",
                            "natOutgoing": "Enabled",
                            "nodeSelector": "all()",
                        }
                    ],
                }
            },
        },
        {
            "apiVersion": "operator.tigera.io/v1",
            "kind": "APIServer",
            "metadata": {"name": "default"},
            "spec": {},
        },
        {
            "apiVersion": "operator.tigera.io/v1",
            "kind": "Goldmane",
            "metadata": {"name": "default"},
        },
        {
            "apiVersion": "operator.tigera.io/v1",
            "kind": "Whisker",
            "metadata": {"name": "default"},
        },
    ]


def install_calico(kubeconfig: str, cluster_cidr: str):
    version = "3.30.3"  # TODO: custom version

    k8s_client = config.new_client_from_config(config_file=kubeconfig)
    utils.create_from_yaml(
        k8s_client,
        f"https://raw.githubusercontent.com/projectcalico/calico/v{version}/manifests/operator-crds.yaml",
    )
    utils.create_from_yaml(
        k8s_client,
        f"https://raw.githubusercontent.com/projectcalico/calico/v{version}/manifests/tigera-operator.yaml",
    )

    for resource in create_calico_config(cluster_cidr):
        utils.create_from_dict(k8s_client, resource)
