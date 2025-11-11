from clusters import Cluster
from .execution import TestEntity


def generate_test_matrix(
    clusters: list[Cluster],
) -> tuple[list[TestEntity], list[TestEntity]]:
    pods = [
        TestEntity(
            name=p.name,
            namespace=ns,
            cluster_name=c.name,
            type="pod",
            ip=p.ip,
            test_suite=["ping", "curl"],
            color=c.color,
        )
        for c in clusters
        for ns in c.namespaces
        for p in c.pods[ns]
    ]

    services = [
        TestEntity(
            name=s.name,
            namespace=ns,
            cluster_name=c.name,
            type="service",
            ip=s.cluster_ip,
            test_suite=["curl"],
            color=c.color,
        )
        for c in clusters
        for ns in c.namespaces
        for s in c.services[ns]
    ]

    internet = TestEntity(
        name="internet",
        namespace="",
        type="external",
        ip="8.8.8.8",
        test_suite=["ping"],
    )

    sources = pods
    destinations = pods + services + [internet]

    return sources, destinations
