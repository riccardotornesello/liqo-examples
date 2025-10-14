def get_pod_ip(kube_client, namespace, pod):
    pod_obj = kube_client.read_namespaced_pod(pod, namespace)
    return pod_obj.status.pod_ip
