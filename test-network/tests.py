from time import sleep
from dataclasses import dataclass
from typing import Any, Literal
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

        match self.test_type:
            case "ping":
                self.result = test_ping(**test_params)
            case "curl":
                self.result = test_curl(**test_params)
            case _:
                raise ValueError(f"Unknown test type: {self.test_type}")


@dataclass
class TestEntity:
    name: str
    namespace: str
    type: Literal["pod", "service", "external"]
    ip: str
    test_suite: list[Literal["ping", "curl"]]
    color: str | None = None
    cluster_name: str | None = None


def test_curl(
    kubeconfig_location: str,
    namespace: str,
    pod: str,
    target_ip: str,
    dst_hostname: str,
) -> bool:
    """
    Tests HTTP connectivity from a source pod to a target IP using curl.

    Executes a curl command in the source pod with a 1-second timeout and
    checks if the HTTP response code is 200 and the response body contains
    the expected hostname string.

    Args:
        kubeconfig_location (str): Path to the kubeconfig file.
        namespace (str): The namespace of the source pod.
        pod (str): The name of the source pod.
        target_ip (str): The target IP address to test connectivity to.
        dst_hostname (str): The expected hostname in the HTTP response.

    Returns:
        bool: True if the curl request succeeds with HTTP 200 and contains
              the expected hostname, False otherwise.
    """
    kube_client = client.CoreV1Api(
        api_client=config.new_client_from_config(kubeconfig_location)
    )

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
                "-w",
                "\n%{http_code}",
                f"http://{target_ip}:80?source={pod}",
            ],
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False,
        )

        # Split response body and status code
        lines = resp.strip().split("\n")
        if len(lines) < 2:
            return False

        status_code = lines[-1]
        received_hostname_str = _find_hostname_line(lines)

        # Check both status code and hostname in response body
        if status_code != "200":
            return False

        expected_hostname_str = f"Hostname: {dst_hostname}"
        if received_hostname_str != expected_hostname_str:
            print(
                f"Expected hostname '{expected_hostname_str}' but got '{received_hostname_str}'"
            )
            return False

        return True

    except Exception as e:
        print("Curl test exception:", e)
        return False


def test_ping(
    kubeconfig_location: str, namespace: str, pod: str, target_ip: str, **_: Any
) -> bool:
    """
    Tests ICMP connectivity from a source pod to a target IP using ping.

    Executes a single ping command in the source pod with a 1-second timeout
    and checks if a response is received.

    Args:
        kubeconfig_location (str): Path to the kubeconfig file.
        namespace (str): The namespace of the source pod.
        pod (str): The name of the source pod.
        target_ip (str): The target IP address to test connectivity to.

    Returns:
        bool: True if the ping succeeds (1 packet received), False otherwise.
    """
    kube_client = client.CoreV1Api(
        api_client=config.new_client_from_config(kubeconfig_location)
    )

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
        print("Ping test exception:", e)
        return False


def run_tests(
    sources: list[TestEntity],
    destinations: list[TestEntity],
    clusters: dict,
    remapped_cidrs: dict,
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
            if (
                destination.cluster_name
                and source.cluster_name != destination.cluster_name
            ):
                target_ip = remap_ip(
                    target_ip,
                    remapped_cidrs[destination.cluster_name],
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


def _find_hostname_line(lines: list[str]) -> str | None:
    """
    Finds the line containing the hostname in a list of strings.

    Args:
        lines (list[str]): List of strings to search.

    Returns:
        str | None: The line containing the hostname, or None if not found.
    """

    return next((x for x in lines if x.startswith("Hostname: ")), None)
