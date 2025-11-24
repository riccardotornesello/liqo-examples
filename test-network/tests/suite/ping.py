from typing import Any
from kubernetes import client, config, stream


def test_ping(
    kubeconfig_location: str,
    namespace: str,
    pod: str,
    target_ip: str,
    **_: Any,
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
