from time import sleep
from dataclasses import dataclass
from typing import Literal
import concurrent.futures

from kubernetes import client, config, stream
from tqdm import tqdm

from resources import BaseResource
from network import remap_ip


class TestManager:
    def __init__(self, test_name, resources: list[BaseResource] = []):
        self.test_name = test_name
        self.resources: list[BaseResource] = resources

    def __enter__(self):
        print(f"========== Setting up test: {self.test_name} ==========")
        for resource in self.resources:
            resource.create()

        # Wait a bit for resources to be applied
        sleep(1)

    def __exit__(self, exc_type, exc_value, traceback):
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

    def run(self):
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


def test_curl(kubeconfig, namespace, pod, target_ip):
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


def test_ping(kubeconfig, namespace, pod, target_ip):
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
    max_workers=5,
) -> list[Test]:
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
