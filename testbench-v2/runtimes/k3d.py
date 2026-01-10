import yaml
import subprocess
from config import CNIEnum


def create_k3d_config(
    nodes: int,
    cluster_cidr: str,
    service_cidr: str,
) -> dict:
    return {
        "apiVersion": "k3d.io/v1alpha5",
        "kind": "Simple",
        "image": "docker.io/rancher/k3s:v1.30.2-k3s2",  # TODO
        "servers": 1,
        "agents": nodes - 1,
        "options": {
            "k3s": {
                "extraArgs": [
                    {
                        "arg": f"--cluster-cidr={cluster_cidr}",
                        "nodeFilters": ["server:*"],
                    },
                    {
                        "arg": f"--service-cidr={service_cidr}",
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
                        for i in range(1, nodes)
                    ],
                ],
            }
        },
    }


def create_k3d_cluster(
    nodes: int,
    cluster_cidr: str,
    service_cidr: str,
    cni: CNIEnum,
):
    config = create_k3d_config(
        nodes=nodes,
        cluster_cidr=cluster_cidr,
        service_cidr=service_cidr,
    )
    config_yaml = yaml.dump(config)

    additional_args = []

    if cni != CNIEnum.flannel:
        additional_args.extend(
            [
                "--k3s-arg",
                "--flannel-backend=none@server:*",
                "--k3s-arg",
                "--disable-network-policy@server:*",
            ]
        )

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


if __name__ == "__main__":
    # Example usage
    create_k3d_cluster(
        nodes=3,
        cluster_cidr="10.200.0.0/16",
        service_cidr="10.201.0.0/16",
    )
