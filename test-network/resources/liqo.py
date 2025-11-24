from .base import CustomResource


class FirewallConfigurationResource(CustomResource):
    """
    Represents a Liqo FirewallConfiguration custom resource.

    Manages firewall configuration resources in the networking.liqo.io API group.
    """

    CR_GROUP = "networking.liqo.io"
    CR_VERSION = "v1beta1"
    CR_PLURAL = "firewallconfigurations"


class NetworkResource(CustomResource):
    """
    Represents a Liqo Network custom resource.

    Manages network resources in the ipam.liqo.io API group, typically used
    for retrieving remapped CIDR information.
    """

    CR_GROUP = "ipam.liqo.io"
    CR_VERSION = "v1alpha1"
    CR_PLURAL = "networks"
