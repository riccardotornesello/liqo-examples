#!/bin/bash

set -e

here="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# shellcheck source=/dev/null
source "$here/../../common.sh"
source "$here/../utils.sh"


CLUSTER_NAME_CONSUMER=rome
CLUSTER_NAME_PROVIDER=milan

KUBECONFIG_CONSUMER=liqo_kubeconf_rome
KUBECONFIG_PROVIDER=liqo_kubeconf_milan

POD_CIDR="10.200.0.0/16"
SERVICES_CIDR="10.201.0.0/16"

MANIFEST_CONSUMER="$here/manifests/resources_consumer.yaml"
MANIFEST_PROVIDER="$here/manifests/resources_provider.yaml"
MANIFEST_OFFLOADED="$here/manifests/resources_offloaded.yaml"


select_executor() {
    question "Select the Kubernetes executor"

    PS3="Select the executor: "
    options=("k3d" "Exit") # TODO: kind

    select opt in "${options[@]}"; do
        case $opt in
            "k3d")
                K8S_EXECUTOR="k3d"
                success "✔ Executor selected: $K8S_EXECUTOR"
                break
                ;;
            "Exit")
                echo "Quitting."
                exit 0
                ;;
            *)
                error "Invalid option: $REPLY. Please try again."
                ;;
        esac
    done
}


select_cni() {
    question "Select the CNI to install"

    PS3="Select the CNI: "
    options=("Flannel" "Exit") # TODO: kindnet, calico, cilium

    select opt in "${options[@]}"; do
        case $opt in
            "Flannel")
                # Convert the selection to lowercase for consistency.
                CNI_PLUGIN=$(echo "$opt" | tr '[:upper:]' '[:lower:]')
                success "✔ CNI selected: $CNI_PLUGIN"
                break
                ;;
            "Exit")
                echo "Quitting."
                exit 0
                ;;
            *)
                error "Invalid option: $REPLY. Please try again."
                ;;
        esac
    done
}


select_cache_option() {
    question "Do you want to enable the image cache? (recommended)"

    read -p "Enable image cache? [Y/n] " -n 1 -r
    REPLY=${REPLY,,}

    echo

    if [[ $REPLY =~ ^[Nn]$ ]]; then
        CACHE_ENABLED="n"
        success "✔ Cache disabled."
    else
        CACHE_ENABLED="y"
        success "✔ Cache enabled."
    fi
}


setup_k3d() {
    # 1. Prepare the environment
    check_requirements "k3d"

    delete_k3d_clusters "$CLUSTER_NAME_CONSUMER" "$CLUSTER_NAME_PROVIDER"

    # 2. Create the clusters
    create_k3d_cluster "$CLUSTER_NAME_CONSUMER" "$here/manifests/k3d_consumer.yaml"
    create_k3d_cluster "$CLUSTER_NAME_PROVIDER" "$here/manifests/k3d_provider.yaml"

    # 3. Save the kubeconfig files
    K3D_KUBECONFIG_CONSUMER_LOCATION=$(get_k3d_kubeconfig $CLUSTER_NAME_CONSUMER)
    K3D_KUBECONFIG_PROVIDER_LOCATION=$(get_k3d_kubeconfig $CLUSTER_NAME_PROVIDER)

    cp "$K3D_KUBECONFIG_CONSUMER_LOCATION" "$here/$KUBECONFIG_CONSUMER"
    cp "$K3D_KUBECONFIG_PROVIDER_LOCATION" "$here/$KUBECONFIG_PROVIDER"

    # 4. Install Liqo
    # TODO: node selector option
    install_liqo_k3d_version "$CLUSTER_NAME_CONSUMER" "$KUBECONFIG_CONSUMER" "$POD_CIDR" "$SERVICES_CIDR" "https://github.com/liqotech/liqo" "v1.0.1" "$here/manifests/k3d_consumer_values.yaml"
    install_liqo_k3d_version "$CLUSTER_NAME_PROVIDER" "$KUBECONFIG_PROVIDER" "$POD_CIDR" "$SERVICES_CIDR" "https://github.com/liqotech/liqo" "v1.0.1" ""
}


setup_infrastructure() {
    # 1. Peer the clusters
    peer_clusters "$KUBECONFIG_CONSUMER" "$KUBECONFIG_PROVIDER"

    # 2. Prepare the namespaces
    create_namespace "$KUBECONFIG_CONSUMER" offloaded
    create_namespace "$KUBECONFIG_CONSUMER" consumer-local
    create_namespace "$KUBECONFIG_PROVIDER" provider-local

    # 3. Offload a namespace
    offload_namespace "$KUBECONFIG_CONSUMER" offloaded

    # 4. Deploy some demo resources
    apply_resources "$KUBECONFIG_CONSUMER" "$MANIFEST_CONSUMER"
    apply_resources "$KUBECONFIG_PROVIDER" "$MANIFEST_PROVIDER"
    apply_resources "$KUBECONFIG_CONSUMER" "$MANIFEST_OFFLOADED"
}

# TODO: select version

# TODO: select_executor
# TODO: select_cni
# TODO: select_cache_option

setup_k3d
setup_infrastructure
