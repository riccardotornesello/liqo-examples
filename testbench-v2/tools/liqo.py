import subprocess

from tools.base import Tool


class LiqoTool(Tool):
    runtime: str
    cluster_id: str
    kubeconfig: str
    version: str
    api_server_url: str | None
    pod_cidr: str | None
    service_cidr: str | None

    def __init__(
        self,
        runtime: str,
        cluster_id: str,
        kubeconfig: str,
        version: str,
        api_server_url: str | None = None,
        pod_cidr: str | None = None,
        service_cidr: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.runtime = runtime
        self.cluster_id = cluster_id
        self.kubeconfig = kubeconfig
        self.version = version
        self.api_server_url = api_server_url
        self.pod_cidr = pod_cidr
        self.service_cidr = service_cidr

    def install(self) -> None:
        print(f"Installing Liqo version {self.version}")

        repo_url = None
        version_hash = None
        if self.version is not None and self.version != "latest":
            (repo_url, version_hash) = self.version.split("@")

        command = [
            "liqoctl",
            "install",
            self.runtime,
        ]

        # Build installation command by adding parameters
        parameters = {
            "--cluster-id": self.cluster_id,
            "--pod-cidr": self.pod_cidr,
            "--service-cidr": self.service_cidr,
            "--kubeconfig": self.kubeconfig,
            "--api-server-url": self.api_server_url,
            "--repo-url": repo_url,
            "--version": version_hash,
        }

        for param, value in parameters.items():
            if value is not None:
                command.extend([param, value])

        # Execute installation command
        subprocess.run(command, check=True)
