from kubernetes import utils, config

from cni.base import CNI


class Calico(CNI):
    version: str

    def __init__(self, version: str = "3.30.3", **kwargs) -> None:
        super().__init__(**kwargs)
        self.version = version

    def install(self) -> None:
        k8s_client = config.new_client_from_config(config_file=self.kubeconfig)

        utils.create_from_yaml(
            k8s_client,
            f"https://raw.githubusercontent.com/projectcalico/calico/v{self.version}/manifests/operator-crds.yaml",
        )
        utils.create_from_yaml(
            k8s_client,
            f"https://raw.githubusercontent.com/projectcalico/calico/v{self.version}/manifests/tigera-operator.yaml",
        )

        for resource in self._gen_config():
            utils.create_from_dict(k8s_client, resource)

    def _gen_config(self) -> list[dict]:
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
                                "cidr": self.cidr,
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
