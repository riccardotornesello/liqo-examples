from kubernetes import client, config, stream


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


def _find_hostname_line(lines: list[str]) -> str | None:
    """
    Finds the line containing the hostname in a list of strings.

    Args:
        lines (list[str]): List of strings to search.

    Returns:
        str | None: The line containing the hostname, or None if not found.
    """

    return next((x for x in lines if x.startswith("Hostname: ")), None)
