import kubernetes
import yaml


class BaseResource:
    """
    Base class for Kubernetes resources with common functionality.

    Provides common attributes and initialization logic for all resource types.
    Subclasses must implement create, delete, and get methods.

    Attributes:
        kubeconfig_path (str): Path to the kubeconfig file.
        namespace (str | None): The namespace where the resource is located.
        name (str | None): The name of the resource.
        options: dict: Additional options for resource configuration.
        BODY_LOCATION (str | None): Path to the YAML file defining the resource body.
    """

    kubeconfig_path: str
    namespace: str | None
    name: str | None
    options: dict

    BODY_LOCATION: str | None

    def __init__(
        self,
        kubeconfig_path: str,
        namespace: str | None = None,
        name: str | None = None,
        options: dict = {},
    ):
        """
        Initializes a BaseResource instance.

        Args:
            kubeconfig_path (str): Path to the kubeconfig file.
            namespace (str | None): The namespace where the resource will be created.
            name (str | None): The name of the resource.
        """
        self.kubeconfig_path = kubeconfig_path
        self.namespace = namespace
        self.name = name
        self.options = options

    def _get_body_content(self) -> dict:
        """
        Generates and returns the resource body without namespace and name.

        Returns:
            dict: The resource definition body.
        """

        if self.BODY_LOCATION:
            with open(self.BODY_LOCATION, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)

        else:
            raise ValueError("BODY_LOCATION must be set to load the resource body.")

    def _get_body(self) -> dict:
        """
        Generates and returns the resource body.

        Returns:
            dict: The resource definition body.
        """

        body = self._get_body_content()

        body["metadata"] = body.get("metadata", {})
        body["metadata"]["namespace"] = self.namespace
        body["metadata"]["name"] = self.name

        return body

    def create(self):
        """
        Creates the resource in the Kubernetes cluster.

        Must be implemented by subclasses.

        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError

    def delete(self, exception_on_not_found: bool = False):
        """
        Deletes the resource from the Kubernetes cluster.

        Must be implemented by subclasses.

        Args:
            exception_on_not_found (bool, optional): Whether to raise an exception if
                the resource is not found. Defaults to False.

        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError

    def get(self, name: str, namespace: str):
        """
        Retrieves the resource from the Kubernetes cluster.

        Must be implemented by subclasses.

        Args:
            name (str): The name of the resource.
            namespace (str): The namespace of the resource.

        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError


class CustomResource(BaseResource):
    """
    Base class for Kubernetes Custom Resources.

    Provides methods to create, delete, and retrieve custom resources using
    the Kubernetes CustomObjectsApi. Subclasses must define CR_GROUP, CR_VERSION,
    and CR_PLURAL class attributes.

    Class Attributes:
        CR_GROUP (str): The API group of the custom resource.
        CR_VERSION (str): The API version of the custom resource.
        CR_PLURAL (str): The plural name of the custom resource.
    """

    CR_GROUP = ""
    CR_VERSION = ""
    CR_PLURAL = ""

    def create(self):
        """
        Creates the custom resource in the Kubernetes cluster.

        Returns:
            dict: The created custom resource object.

        Raises:
            ValueError: If namespace or name is not set.
        """
        if not self.namespace:
            raise ValueError("Namespace must be set to create the resource.")

        if not self.name:
            raise ValueError("Name must be set to create the resource.")

        api_instance = kubernetes.client.CustomObjectsApi(
            api_client=kubernetes.config.new_client_from_config(self.kubeconfig_path)
        )
        body = self._get_body()

        return api_instance.create_namespaced_custom_object(
            group=self.CR_GROUP,
            version=self.CR_VERSION,
            namespace=self.namespace,
            plural=self.CR_PLURAL,
            body=body,
        )

    def delete(self, exception_on_not_found: bool = False):
        """
        Deletes the custom resource from the Kubernetes cluster.

        Args:
            exception_on_not_found (bool, optional): Whether to raise an exception if
                the resource is not found. Defaults to False.

        Returns:
            dict | None: The deletion status object, or None if not found and
                exception_on_not_found is False.

        Raises:
            kubernetes.client.exceptions.ApiException: If deletion fails for reasons
                other than the resource not being found (when exception_on_not_found is False).
            ValueError: If namespace or name is not set.
        """
        if not self.namespace:
            raise ValueError("Namespace must be set to delete the resource.")

        if not self.name:
            raise ValueError("Name must be set to delete the resource.")

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
        """
        Retrieves the custom resource from the Kubernetes cluster.

        Returns:
            dict: The custom resource object.

        Raises:
            ValueError: If namespace or name is not set.
        """
        if not self.namespace:
            raise ValueError("Namespace must be set to get the resource.")

        if not self.name:
            raise ValueError("Name must be set to get the resource.")

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

    def list(self) -> list[dict]:
        """
        Lists all instances of the custom resource in the specified namespace.

        Returns:
            list[dict]: A list of custom resource objects.
        """
        api_instance = kubernetes.client.CustomObjectsApi(
            api_client=kubernetes.config.new_client_from_config(self.kubeconfig_path)
        )

        if self.namespace:
            response = api_instance.list_namespaced_custom_object(
                group=self.CR_GROUP,
                version=self.CR_VERSION,
                namespace=self.namespace,
                plural=self.CR_PLURAL,
            )
        else:
            response = api_instance.list_cluster_custom_object(
                group=self.CR_GROUP,
                version=self.CR_VERSION,
                plural=self.CR_PLURAL,
            )

        return response.get("items", [])
