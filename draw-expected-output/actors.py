class Actor:
    actor_type: str

    name: str
    owner_cluster: str
    hosting_cluster: str

    block_ingress: str
    offloaded_isolation: str

    def __init__(
        self,
        name: str,
        owner_cluster: str,
        hosting_cluster: str,
        block_ingress: str,
        offloaded_isolation: str,
    ):
        self.name = name
        self.owner_cluster = owner_cluster
        self.hosting_cluster = hosting_cluster

        self.block_ingress = block_ingress
        self.offloaded_isolation = offloaded_isolation

    def ingress(self, source, destination, next_hop):
        return True

    def egress(self, source, destination, next_hop):
        return True

    def __eq__(self, other):
        return (
            self.name == other.name
            and self.owner_cluster == other.owner_cluster
            and self.hosting_cluster == other.hosting_cluster
        )


class Pod(Actor):
    actor_type = "pod"

    def ingress(self, source: Actor, destination: Actor, next_hop: Actor):
        is_hosted_remotely = self.hosting_cluster != self.owner_cluster

        if not is_hosted_remotely:
            return True

        match self.offloaded_isolation:
            case "off":
                # Always allow all traffic
                return True
            case "peerings":
                # Block connections from other consumers but allow traffic from the same owner or from the cluster's owner
                return (
                    source.owner_cluster == self.owner_cluster
                    or source.owner_cluster == self.hosting_cluster
                )
            case "full":
                # Allow traffic only from the same owner
                return source.owner_cluster == self.owner_cluster
            case _:
                raise ValueError(
                    f"Unknown offloaded_isolation policy: {self.offloaded_isolation}"
                )

    def egress(self, source: Actor, destination: Actor, next_hop: Actor):
        is_hosted_remotely = self.hosting_cluster != self.owner_cluster

        if not is_hosted_remotely:
            return True

        match self.block_ingress:
            case "off":
                # Always allow all traffic
                return True
            case "isolation" | "strict":
                # Allow traffic only to owned resources (owner's cluster or other offloaded resources)
                return destination.owner_cluster == self.owner_cluster
            case _:
                raise ValueError(
                    f"Unknown block_ingress policy: {self.block_ingress}"
                )

        return True


class Gateway(Actor):
    actor_type = "gateway"

    def ingress(self, source: Actor, destination: Actor, next_hop: Actor):
        if source.hosting_cluster != self.hosting_cluster:
            return True

        match self.offloaded_isolation:
            case "off":
                # Allow all traffic
                return True
            case "peerings":
                # Allow traffic from the destination's owner or from the cluster's owner
                return (
                    source.owner_cluster == destination.owner_cluster
                    or source.owner_cluster == self.hosting_cluster
                )
            case "full":
                # Allow traffic only from the destination's owner
                return source.owner_cluster == destination.owner_cluster
            case _:
                raise ValueError(
                    f"Unknown offloaded_isolation policy: {self.offloaded_isolation}"
                )

    def egress(self, source: Actor, destination: Actor, next_hop: Actor):
        if next_hop.actor_type == "gateway":
            return True

        match self.block_ingress:
            case "off":
                # Allow all traffic
                return True
            case "isolation":
                # Allow traffic only to offloaded resources
                return source.owner_cluster == next_hop.owner_cluster
            case "strict":
                # Always block traffic
                return False
            case _:
                raise ValueError(f"Unknown block_ingress policy: {self.block_ingress}")


def test_forwarding(
    from_pod, to_pod, consumer_configuration, provider_configuration, debug=False
):
    pods = {
        "PC": Pod("PC", "C", "C", **consumer_configuration),
        "POC": Pod("POC", "C", "C", **consumer_configuration),
        "POP": Pod("POP", "C", "P", **provider_configuration),
        "PP": Pod("PP", "P", "P", **provider_configuration),
        "PXP": Pod("PXP", "X", "P", **provider_configuration),
    }

    gateways = {
        "C": Gateway("GC", "C", "C", **consumer_configuration),
        "P": Gateway("GP", "P", "P", **provider_configuration),
    }

    def debug_print(msg):
        if debug:
            print(msg)

    def forward(source: Actor, destination: Actor, curr_hop: Actor = None):
        if source == destination:
            debug_print("Destination reached")
            return True

        if curr_hop is None:
            curr_hop = source

        if curr_hop.actor_type == "gateway":
            if curr_hop.hosting_cluster != destination.hosting_cluster:
                next_hop = gateways[destination.hosting_cluster]
            else:
                next_hop = destination

        elif curr_hop.actor_type == "pod":
            if curr_hop.hosting_cluster != destination.hosting_cluster:
                next_hop = gateways[curr_hop.hosting_cluster]
            else:
                next_hop = destination

        else:
            raise ValueError(f"Unknown actor type: {curr_hop.actor_type}")

        if curr_hop == next_hop:
            debug_print("Destination reached")
            return True

        debug_print(f"{curr_hop.name} -> {next_hop.name}")

        if not curr_hop.egress(source, destination, next_hop):
            debug_print(f"Blocked at {curr_hop.name} (egress)")
            return False

        if not next_hop.ingress(source, destination, curr_hop):
            debug_print(f"Blocked at {next_hop.name} (ingress)")
            return False

        return forward(source, destination, curr_hop=next_hop)

    return forward(pods[from_pod], pods[to_pod])


if __name__ == "__main__":
    consumer_configuration = {
        "block_ingress": "isolation",
        "offloaded_isolation": "peerings",
    }

    provider_configuration = {
        "block_ingress": "strict",
        "offloaded_isolation": "peerings",
    }

    print("===== PC -> PP =====")
    test_forwarding("PC", "PP", consumer_configuration, provider_configuration)

    print("===== PC -> POP =====")
    test_forwarding("PC", "POP", consumer_configuration, provider_configuration)

    print("===== POP -> PC =====")
    test_forwarding("POP", "PC", consumer_configuration, provider_configuration)
