from time import sleep

from kubernetes import client, config, stream

from resources import BaseResource


class TestManager:
    def __init__(self, test_name, resources: list[BaseResource] = []):
        self.test_name = test_name
        self.resources: list[BaseResource] = resources

    def __enter__(self):
        print(f"========== Setting up test: {self.test_name} ==========")
        for resource in self.resources:
            resource.create()
        sleep(1)

    def __exit__(self, exc_type, exc_value, traceback):
        print(f"========== Tearing down test: {self.test_name} ==========")
        for resource in self.resources:
            resource.delete()


class TestResult:
    def __init__(self, destination: dict):
        self.destination = destination
        self.results = {}

    def add_result(self, test_type: str, result: bool):
        self.results[test_type] = result

    def get_result(self, test_type: str):
        return self.results.get(test_type, None)


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


def run_tests(sources, destinations, clusters, remapped_cidrs):
    # TODO: parallelize
    # TODO: use more TypedDicts and clean code

    results = {}

    for source in sources:
        results[source["name"]] = {}

        for destination in destinations:
            if source["name"] == destination["name"]:
                continue

            if (
                destination["type"] == "service"
                and source["cluster"] != destination["cluster"]
            ):
                continue

            results[source["name"]][destination["namespace"]] = results[
                source["name"]
            ].get(destination["namespace"], {})
            results[source["name"]][destination["namespace"]][destination["name"]] = (
                TestResult(destination)
            )

            target_ip = destination["ip"]
            if source["cluster"] != destination["cluster"]:
                # TODO: handle remapped CIDR other than /16
                target_ip = target_ip.split(".")
                target_remap_cidr = remapped_cidrs[destination["cluster"]].split(".")
                target_ip[0] = target_remap_cidr[0]
                target_ip[1] = target_remap_cidr[1]
                target_ip = ".".join(target_ip)

            print(
                f"Testing curl from pod {source['name']} ({source['ip']}) in cluster {source['cluster']} to {destination['name']} ({destination['ip']}) in cluster {destination['cluster']} via IP {target_ip}"
            )
            if test_curl(
                clusters[source["cluster"]].kubeconfig,
                source["namespace"],
                source["name"],
                target_ip,
            ):
                results[source["name"]][destination["namespace"]][
                    destination["name"]
                ].add_result("curl", True)
                print("  \x1b[32mSUCCESS\x1b[0m")
            else:
                results[source["name"]][destination["namespace"]][
                    destination["name"]
                ].add_result("curl", False)
                print("  \x1b[31mFAILURE\x1b[0m")

            if destination["type"] != "service":
                print(
                    f"Testing ping from pod {source['name']} ({source['ip']}) in cluster {source['cluster']} to {destination['name']} ({destination['ip']}) in cluster {destination['cluster']} via IP {target_ip}"
                )
                if test_ping(
                    clusters[source["cluster"]].kubeconfig,
                    source["namespace"],
                    source["name"],
                    target_ip,
                ):
                    results[source["name"]][destination["namespace"]][
                        destination["name"]
                    ].add_result("ping", True)
                    print("  \x1b[32mSUCCESS\x1b[0m")
                else:
                    results[source["name"]][destination["namespace"]][
                        destination["name"]
                    ].add_result("ping", False)
                    print("  \x1b[31mFAILURE\x1b[0m")

    return results
