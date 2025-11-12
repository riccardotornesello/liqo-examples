import kubernetes

from .base import BaseResource


class NetworkPolicyResource(BaseResource):
    """
    Represents a Kubernetes NetworkPolicy resource.

    Provides methods to create and delete NetworkPolicy resources.
    """

    def create(self):
        """
        Creates the NetworkPolicy in the Kubernetes cluster.

        Returns:
            V1NetworkPolicy: The created NetworkPolicy object.
        """
        api_instance = kubernetes.client.NetworkingV1Api(
            api_client=kubernetes.config.new_client_from_config(self.kubeconfig_path)
        )
        body = self._get_body()

        return api_instance.create_namespaced_network_policy(
            namespace=self.namespace, body=body
        )

    def delete(self, exception_on_not_found: bool = False):
        """
        Deletes the NetworkPolicy from the Kubernetes cluster.

        Args:
            exception_on_not_found (bool, optional): Whether to raise an exception if
                the resource is not found. Defaults to False.

        Returns:
            V1Status | None: The deletion status object, or None if not found and
                exception_on_not_found is False.

        Raises:
            kubernetes.client.exceptions.ApiException: If deletion fails for reasons
                other than the resource not being found (when exception_on_not_found is False).
        """
        name = self.name
        namespace = self.namespace

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
