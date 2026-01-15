from abc import ABC, abstractmethod

from config import CNIEnum, ToolsConfig


class Cluster(ABC):
    name: str
    nodes: int
    cluster_cidr: str
    service_cidr: str
    cni: CNIEnum
    tools: ToolsConfig

    def __init__(
        self,
        name: str,
        nodes: int,
        cluster_cidr: str,
        service_cidr: str,
        cni: CNIEnum,
        tools: ToolsConfig,
    ):
        self.name = name
        self.nodes = nodes
        self.cluster_cidr = cluster_cidr
        self.service_cidr = service_cidr
        self.cni = cni
        self.tools = tools

    def create(self) -> None:
        self.init_cluster()
        self.install_cni()
        self.install_tools()

    @abstractmethod
    def init_cluster(self) -> None:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def install_cni(self) -> None:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def install_tools(self) -> None:
        raise NotImplementedError("Subclasses must implement this method.")
