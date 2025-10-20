from kubernetes import client, config, stream


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
