import yaml
import os
import subprocess

from clusters.base import Cluster
from cni.base import CNI
from cni.calico import Calico
from config import CNIEnum


class K3d(Cluster):
    IMAGE = "docker.io/rancher/k3s:v1.30.2-k3s2"  # TODO custom image

    def create(self):
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
        kubeconfig_location = f"kubeconfigs/{self.name}.yaml"

        os.makedirs(os.path.dirname(kubeconfig_location), exist_ok=True)

        with open(kubeconfig_location, "w") as f:
            f.write(kubeconfig_content)

        # Install the selected CNI plugin
        cni: CNI

        match self.cni:
            case CNIEnum.calico:
                cni = Calico(kubeconfig=kubeconfig_location, cidr=self.cluster_cidr)
            case CNIEnum.flannel:
                # Skip installation as flannel is default
                pass
            case _:
                raise ValueError(f"Unsupported CNI: {self.cni}")

        if cni is not None:
            cni.install(
                kubeconfig=kubeconfig_location,
                cidr=self.cluster_cidr,
            )

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
