import kubernetes
import yaml


class BaseResource:
    def __init__(
        self,
        kubeconfig_path: str,
        namespace: str,
        name: str,
        body_location: str | None = None,
    ):
        self.kubeconfig_path = kubeconfig_path
        self.namespace = namespace
        self.name = name

        if body_location:
            with open(body_location, "r", encoding="utf-8") as f:
                self.body = yaml.safe_load(f)
            self.body["metadata"] = self.body.get("metadata", {})
            self.body["metadata"]["namespace"] = namespace
            self.body["metadata"]["name"] = name

    def create(self):
        raise NotImplementedError

    def delete(self, exception_on_not_found: bool = False):
        raise NotImplementedError

    def get(self, name: str, namespace: str):
        raise NotImplementedError

    def set_body(self, body: dict):
        self.body = body
        self.body["metadata"] = self.body.get("metadata", {})
        self.body["metadata"]["namespace"] = self.namespace
        self.body["metadata"]["name"] = self.name


class CustomResource(BaseResource):
    CR_GROUP = ""
    CR_VERSION = ""
    CR_PLURAL = ""

    def create(self):
        api_instance = kubernetes.client.CustomObjectsApi(
            api_client=kubernetes.config.new_client_from_config(self.kubeconfig_path)
        )
        return api_instance.create_namespaced_custom_object(
            group=self.CR_GROUP,
            version=self.CR_VERSION,
            namespace=self.namespace,
            plural=self.CR_PLURAL,
            body=self.body,
        )

    def delete(self, exception_on_not_found: bool = False):
        api_instance = kubernetes.client.CustomObjectsApi(
            api_client=kubernetes.config.new_client_from_config(self.kubeconfig_path)
        )

        try:
            return api_instance.delete_namespaced_custom_object(
                group=self.CR_GROUP,
                version=self.CR_VERSION,
                namespace=self.namespace,
                plural=self.CR_PLURAL,
                name=self.name,
            )
        except kubernetes.client.exceptions.ApiException as e:
            if e.status == 404 and not exception_on_not_found:
                return None
            else:
                raise e

    def get(self):
        api_instance = kubernetes.client.CustomObjectsApi(
            api_client=kubernetes.config.new_client_from_config(self.kubeconfig_path)
        )
        return api_instance.get_namespaced_custom_object(
            group=self.CR_GROUP,
            version=self.CR_VERSION,
            namespace=self.namespace,
            plural=self.CR_PLURAL,
            name=self.name,
        )


class NetworkPolicyResource(BaseResource):
    def create(self):
        api_instance = kubernetes.client.NetworkingV1Api(
            api_client=kubernetes.config.new_client_from_config(self.kubeconfig_path)
        )
        return api_instance.create_namespaced_network_policy(
            namespace=self.namespace, body=self.body
        )

    def delete(self, exception_on_not_found: bool = False):
        name = self.body["metadata"]["name"]
        namespace = self.body["metadata"]["namespace"]

        api_instance = kubernetes.client.NetworkingV1Api(
            api_client=kubernetes.config.new_client_from_config(self.kubeconfig_path)
        )

        try:
            return api_instance.delete_namespaced_network_policy(
                name=name,
                namespace=namespace,
            )
        except kubernetes.client.exceptions.ApiException as e:
            if e.status == 404 and not exception_on_not_found:
                return None
            else:
                raise e


class FirewallConfigurationResource(CustomResource):
    CR_GROUP = "networking.liqo.io"
    CR_VERSION = "v1beta1"
    CR_PLURAL = "firewallconfigurations"


class NetworkResource(CustomResource):
    CR_GROUP = "ipam.liqo.io"
    CR_VERSION = "v1alpha1"
    CR_PLURAL = "networks"
