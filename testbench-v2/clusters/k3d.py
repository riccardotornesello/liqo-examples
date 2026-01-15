import yaml
import os
import subprocess
from kubernetes import utils, config, client

from clusters.base import Cluster
from cni.base import CNI
from cni.calico import Calico
from config import CNIEnum
from tools.liqo import LiqoTool


class K3d(Cluster):
    IMAGE = "docker.io/rancher/k3s:v1.30.2-k3s2"  # TODO custom image

    def init_cluster(self) -> None:
        config = self._gen_config()
        config_yaml = yaml.dump(config)

        additional_args = []

        if self.cni != CNIEnum.flannel:
            additional_args.extend(
                [
                    "--k3s-arg",
                    "--flannel-backend=none@server:*",
                    "--k3s-arg",
                    "--disable-network-policy@server:*",
                ]
            )

        # Create the cluster using k3d CLI
        subprocess.run(
            [
                "k3d",
                "cluster",
                "create",
                self.name,
                "--config",
                "-",
                "--kubeconfig-update-default=false",
            ]
            + additional_args,
            input=config_yaml.encode(),
            check=True,
        )

        # Save kubeconfig content
        kubeconfig_content = self._get_kubeconfig_content()
        kubeconfig_location = self._get_kubeconfig_location()

        os.makedirs(os.path.dirname(kubeconfig_location), exist_ok=True)

        with open(kubeconfig_location, "w") as f:
            f.write(kubeconfig_content)

    def install_cni(self) -> None:
        kubeconfig_location = self._get_kubeconfig_location()

        # Install the selected CNI plugin
        cni: CNI | None = None

        match self.cni:
            case CNIEnum.calico:
                cni = Calico(kubeconfig=kubeconfig_location, cidr=self.cluster_cidr)
            case CNIEnum.flannel:
                # Skip installation as flannel is default
                pass
            case _:
                raise ValueError(f"Unsupported CNI: {self.cni}")

        if cni is not None:
            cni.install()

    def install_tools(self) -> None:
        kubeconfig_location = self._get_kubeconfig_location()

        # Install Liqo
        if self.tools.liqo:
            liqo = LiqoTool(
                runtime="k3s",
                cluster_id=self.name,
                kubeconfig=kubeconfig_location,
                version=self.tools.liqo,
                api_server_url=self._get_api_server_address(),
                pod_cidr=self.cluster_cidr,
                service_cidr=self.service_cidr,
            )
            liqo.install()

    def _get_kubeconfig_location(self) -> str:
        return f"out/kubeconfigs/{self.name}.yaml"

    def _get_kubeconfig_content(self) -> str:
        result = subprocess.run(
            ["k3d", "kubeconfig", "get", self.name],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout

    def _gen_config(self) -> dict:
        return {
            "apiVersion": "k3d.io/v1alpha5",
            "kind": "Simple",
            "image": self.IMAGE,
            "servers": 1,
            "agents": self.nodes - 1,
            "options": {
                "k3s": {
                    "extraArgs": [
                        {
                            "arg": f"--cluster-cidr={self.cluster_cidr}",
                            "nodeFilters": ["server:*"],
                        },
                        {
                            "arg": f"--service-cidr={self.service_cidr}",
                            "nodeFilters": ["server:*"],
                        },
                    ],
                    "nodeLabels": [
                        {
                            "label": "tier=worker-0",
                            "nodeFilters": ["server:0"],
                        },
                        *[
                            {
                                "label": f"tier=worker-{i}",
                                "nodeFilters": [f"agent:{i - 1}"],
                            }
                            for i in range(1, self.nodes)
                        ],
                    ],
                }
            },
        }

    def _get_api_server_address(self) -> str:
        kubeconfig_location = self._get_kubeconfig_location()
        k8s_client = config.new_client_from_config(config_file=kubeconfig_location)
        v1 = client.CoreV1Api(k8s_client)

        label_selector = "node-role.kubernetes.io/master"

        nodes = v1.list_node(label_selector=label_selector)
        for node in nodes.items:
            for addr in node.status.addresses:
                if addr.type == "InternalIP":
                    return addr.address

        raise RuntimeError("API server address not found")
