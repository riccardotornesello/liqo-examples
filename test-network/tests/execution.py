from dataclasses import dataclass
from typing import Literal
import concurrent.futures

from tqdm import tqdm

from .suite import test_suite
from utils.network import remap_ip
from clusters import Cluster


@dataclass
class Test:
    test_type: Literal["ping", "curl"]
    src_ip: str
    dst_ip: str
    src_name: str
    src_namespace: str
    dst_name: str
    dst_cluster_name: str
    dst_hostname: str
    kubeconfig_location: str
    result: bool | None = None

    def run(self) -> None:
        """
        Executes the test and stores the result.

        Runs the appropriate test function (ping or curl) based on test_type
        and updates the result attribute with the outcome.

        Raises:
            ValueError: If test_type is not "ping" or "curl".
        """
        test_params = {
            "kubeconfig_location": self.kubeconfig_location,
            "namespace": self.src_namespace,
            "pod": self.src_name,
            "target_ip": self.dst_ip,
            "dst_hostname": self.dst_hostname,
        }

        test_function = test_suite.get(self.test_type)
        if test_function is None:
            raise ValueError(f"Unknown test type: {self.test_type}")

        self.result = test_function(**test_params)


@dataclass
class TestEntity:
    """
    Represents an entity involved in network testing.
    It can be a pod, service, or external endpoint.
    It can be a source or destination in tests.

    Attributes:
        name (str): The name of the entity.
        namespace (str): The namespace of the entity.
        type (Literal["pod", "service", "external"]): The type of the entity.
        ip (str): The IP address of the entity.
        test_suite (list[Literal["ping", "curl"]]): List of tests to run against this entity.
        color (str | None): Optional color code for display purposes.
        cluster_name (str | None): The name of the cluster the entity belongs to.
    """

    name: str
    namespace: str
    type: Literal["pod", "service", "external"]
    ip: str
    test_suite: list[Literal["ping", "curl"]]
    color: str | None = None
    cluster_name: str | None = None


def run_tests(
    sources: list[TestEntity],
    destinations: list[TestEntity],
    clusters: list[Cluster],
    max_workers: int = 10,
) -> list[Test]:
    """
    Runs network connectivity tests between all source and destination entities.

    Creates and executes test cases for all valid source-destination pairs,
    running tests in parallel using a thread pool. Tests include:
    - curl tests for both pods and services
    - ping tests for pods only (services don't support ping)

    Steps:
    1. Generate test cases for all valid source-destination pairs
    2. Skip self-to-self tests
    3. Skip cross-cluster service tests (services are cluster-local)
    4. Remap IPs for cross-cluster pod tests
    5. Execute tests in parallel using ThreadPoolExecutor
    6. Display progress with a progress bar

    Args:
        sources (list[TestEntity]): List of source entities to test from.
        destinations (list[TestEntity]): List of destination entities to test to.
        clusters (list[Cluster]): List of clusters for IP remapping.
        max_workers (int, optional): Maximum number of concurrent test threads. Defaults to 5.

    Returns:
        list[Test]: List of Test objects with results populated.
    """
    tests: list[Test] = []

    remapped_cidrs = {c.name: c.remapped_cidrs for c in clusters}
    kubeconfigs = {c.name: c.kubeconfig_location for c in clusters}

    for source in sources:
        for destination in destinations:
            # Skip testing to self
            if source.name == destination.name:
                continue

            # Skip testing service from pod in different cluster
            if (
                destination.type == "service"
                and source.cluster_name != destination.cluster_name
            ):
                continue

            # Remap IP if necessary
            target_ip = destination.ip
            if (
                destination.cluster_name
                and source.cluster_name != destination.cluster_name
            ):
                target_ip = remap_ip(
                    target_ip,
                    remapped_cidrs[source.cluster_name][destination.cluster_name],
                )

            # Create the test list
            for test_type in destination.test_suite:
                tests.append(
                    Test(
                        test_type=test_type,
                        src_ip=source.ip,
                        dst_ip=target_ip,
                        src_name=source.name,
                        src_namespace=source.namespace,
                        dst_name=destination.name,
                        dst_cluster_name=destination.cluster_name,
                        dst_hostname="p"
                        + destination.name[
                            1:
                        ],  # In case of a service, replace the 's' with 'p' to get the pod hostname
                        kubeconfig_location=kubeconfigs[source.cluster_name],
                    )
                )

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(test.run) for test in tests]

        for future in tqdm(
            concurrent.futures.as_completed(futures),
            total=len(futures),
            desc="Running tests",
        ):
            try:
                future.result()
            except Exception as exc:
                print(f"Generated an exception: {exc}")

    return tests
