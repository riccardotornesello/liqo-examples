def get_service_ip(kube_client, namespace, service):
    svc = kube_client.read_namespaced_service(service, namespace)
    return svc.spec.cluster_ip
