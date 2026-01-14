from abc import ABC, abstractmethod

from config import CNIEnum


class Cluster(ABC):
    name: str
    nodes: int
    cluster_cidr: str
    service_cidr: str
    cni: CNIEnum

    def __init__(
        self,
        name: str,
        nodes: int,
        cluster_cidr: str,
        service_cidr: str,
        cni: CNIEnum,
    ):
        self.name = name
        self.nodes = nodes
        self.cluster_cidr = cluster_cidr
        self.service_cidr = service_cidr
        self.cni = cni

    @abstractmethod
    def create(self) -> None:
        raise NotImplementedError("Subclasses must implement this method.")
