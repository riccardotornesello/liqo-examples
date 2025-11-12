from time import sleep

from resources.base import BaseResource


class TestManager:
    """
    Context manager for setting up and tearing down test resources.

    Creates resources before tests run and cleans them up afterwards.

    Attributes:
        test_name (str): The name of the test being run.
        resources (list[BaseResource]): List of resources to create and cleanup.
    """

    def __init__(self, test_name: str, resources: list[BaseResource] = None):
        """
        Initializes a TestManager instance.

        Args:
            test_name (str): The name of the test.
            resources (list[BaseResource], optional): List of resources to manage.
                Defaults to None (empty list).
        """
        self.test_name = test_name
        self.resources: list[BaseResource] = resources if resources is not None else []

    def __enter__(self):
        """
        Sets up test resources when entering the context.

        Steps:
        1. Prints the test setup message
        2. Creates all resources in the cluster
        3. Waits 1 second for resources to be applied
        """
        print(f"========== Setting up test: {self.test_name} ==========")
        for resource in self.resources:
            resource.create()

        # Wait a bit for resources to be applied
        sleep(1)

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Tears down test resources when exiting the context.

        Args:
            exc_type: Exception type if an exception occurred.
            exc_value: Exception value if an exception occurred.
            traceback: Traceback if an exception occurred.
        """
        print(f"========== Tearing down test: {self.test_name} ==========")
        for resource in self.resources:
            resource.delete()
