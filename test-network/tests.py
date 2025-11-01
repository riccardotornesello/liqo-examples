from time import sleep
from dataclasses import dataclass
from typing import Literal
import concurrent.futures

from kubernetes import client, config, stream
from tqdm import tqdm

from resources import BaseResource
from network import remap_ip


class TestManager:
    """
    Context manager for setting up and tearing down test resources.

    Creates resources before tests run and cleans them up afterwards.

    Attributes:
        test_name (str): The name of the test being run.
        resources (list[BaseResource]): List of resources to create and cleanup.
    """

    def __init__(self, test_name: str, resources: list[BaseResource] = None):
        """
        Initializes a TestManager instance.

        Args:
            test_name (str): The name of the test.
            resources (list[BaseResource], optional): List of resources to manage.
                Defaults to None (empty list).
        """
        self.test_name = test_name
        self.resources: list[BaseResource] = resources if resources is not None else []

    def __enter__(self):
        """
        Sets up test resources when entering the context.

        Steps:
        1. Prints the test setup message
        2. Creates all resources in the cluster
        3. Waits 1 second for resources to be applied
        """
        print(f"========== Setting up test: {self.test_name} ==========")
        for resource in self.resources:
            resource.create()

        # Wait a bit for resources to be applied
        sleep(1)

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Tears down test resources when exiting the context.

        Args:
            exc_type: Exception type if an exception occurred.
            exc_value: Exception value if an exception occurred.
            traceback: Traceback if an exception occurred.
        """
        print(f"========== Tearing down test: {self.test_name} ==========")
        for resource in self.resources:
            resource.delete()


@dataclass
class Test:
    test_type: Literal["ping", "curl"]
    src_ip: str
    dst_ip: str
    src_name: str
    src_namespace: str
    dst_name: str
    dst_cluster_name: str
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
        test_params = (
            self.kubeconfig_location,
            self.src_namespace,
            self.src_name,
            self.dst_ip,
        )

        match self.test_type:
            case "ping":
                self.result = test_ping(*test_params)
            case "curl":
                self.result = test_curl(*test_params)
            case _:
                raise ValueError(f"Unknown test type: {self.test_type}")


@dataclass
class TestEntity:
    name: str
    namespace: str
    cluster_name: str
    type: Literal["pod", "service"]
    ip: str


def test_curl(kubeconfig: str, namespace: str, pod: str, target_ip: str) -> bool:
    """
    Tests HTTP connectivity from a source pod to a target IP using curl.

    Executes a curl command in the source pod with a 1-second timeout and
    checks if the HTTP response code is 200.

    Args:
        kubeconfig (str): Path to the kubeconfig file.
        namespace (str): The namespace of the source pod.
        pod (str): The name of the source pod.
        target_ip (str): The target IP address to test connectivity to.

    Returns:
        bool: True if the curl request succeeds with HTTP 200, False otherwise.
    """
    kube_client = client.CoreV1Api(api_client=config.new_client_from_config(kubeconfig))

    try:
        resp = stream.stream(
            kube_client.connect_get_namespaced_pod_exec,
            pod,
            namespace,
            command=[
                "curl",
                "-m",
                "1",
                "-s",
                "-o",
                "/dev/null",
                "-w",
                "%{http_code}",
                f"http://{target_ip}:80",
            ],
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False,
        )
        if resp == "200":
            # TODO: check if the hostname in the response body is correct
            return True
        else:
            return False
    except Exception as e:
        return False


def test_ping(kubeconfig: str, namespace: str, pod: str, target_ip: str) -> bool:
    """
    Tests ICMP connectivity from a source pod to a target IP using ping.

    Executes a single ping command in the source pod with a 1-second timeout
    and checks if a response is received.

    Args:
        kubeconfig (str): Path to the kubeconfig file.
        namespace (str): The namespace of the source pod.
        pod (str): The name of the source pod.
        target_ip (str): The target IP address to test connectivity to.

    Returns:
        bool: True if the ping succeeds (1 packet received), False otherwise.
    """
    kube_client = client.CoreV1Api(api_client=config.new_client_from_config(kubeconfig))

    try:
        resp = stream.stream(
            kube_client.connect_get_namespaced_pod_exec,
            pod,
            namespace,
            command=["ping", "-c", "1", "-W", "1", target_ip],
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False,
        )
        if "1 received" in resp:
            return True
        else:
            return False
    except Exception as e:
        return False


def run_tests(
    sources: list[TestEntity],
    destinations: list[TestEntity],
    clusters: dict,
    remapped_cidrs: dict,
    max_workers: int = 5,
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
        clusters (dict): Dictionary mapping cluster names to Cluster objects.
        remapped_cidrs (dict): Dictionary mapping cluster names to their remapped CIDRs.
        max_workers (int, optional): Maximum number of concurrent test threads. Defaults to 5.

    Returns:
        list[Test]: List of Test objects with results populated.
    """
    tests: list[Test] = []

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
            if source.cluster_name != destination.cluster_name:
                target_ip = remap_ip(
                    target_ip,
                    remapped_cidrs[destination.cluster_name],
                )

            # Create the test list
            tests.append(
                Test(
                    test_type="curl",
                    src_ip=source.ip,
                    dst_ip=destination.ip,
                    src_name=source.name,
                    src_namespace=source.namespace,
                    dst_name=destination.name,
                    dst_cluster_name=destination.cluster_name,
                    kubeconfig_location=clusters[source.cluster_name].kubeconfig,
                )
            )

            if destination.type != "service":
                tests.append(
                    Test(
                        test_type="curl",
                        src_ip=source.ip,
                        dst_ip=destination.ip,
                        src_name=source.name,
                        src_namespace=source.namespace,
                        dst_name=destination.name,
                        dst_cluster_name=destination.cluster_name,
                        kubeconfig_location=clusters[source.cluster_name].kubeconfig,
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
