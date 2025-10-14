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

MANIFEST_CALICO_1=https://raw.githubusercontent.com/projectcalico/calico/v3.30.3/manifests/operator-crds.yaml
MANIFEST_CALICO_2=https://raw.githubusercontent.com/projectcalico/calico/v3.30.3/manifests/tigera-operator.yaml
MANIFEST_CALICO_3="$here/manifests/calico.yaml"

CNI_PLUGINS=("flannel" "calico") # TODO: kindnet, cilium


K8S_EXECUTOR=""
CNI_PLUGIN=""
CACHE_ENABLED=""
RESOURCES_ENABLED=""


function select_executor() {
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


function select_cni() {
    question "Select the CNI to install"

    PS3="Select the CNI: "
    options=("${CNI_PLUGINS[@]}" "Exit")

    select opt in "${options[@]}"; do
        case $opt in
            "flannel"|"calico")
                CNI_PLUGIN=$opt
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


function select_cache_option() {
    question "Do you want to enable the image cache? (recommended)"

    read -p "Enable image cache? [Y/n] " -n 1 -r
    REPLY=${REPLY,,}

    if [[ $REPLY =~ ^[Nn]$ ]]; then
        CACHE_ENABLED="n"
        success "✔ Cache disabled."
    else
        CACHE_ENABLED="y"
        success "✔ Cache enabled."
    fi
}


function select_resources_option() {
    question "Do you want to create demo resources in the clusters?"

    read -p "Create demo resources? [Y/n] " -n 1 -r
    REPLY=${REPLY,,}

    if [[ $REPLY =~ ^[Nn]$ ]]; then
        RESOURCES_ENABLED="n"
        success "✔ Resources creation disabled."
    else
        RESOURCES_ENABLED="y"
        success "✔ Resources creation enabled."
    fi
}


function setup_k3d() {
    # 1. Prepare the environment
    check_requirements "k3d"

    delete_all_k3d_clusters

    # 2. Create the clusters
    # TODO: setup the cache
    if [ "$CNI_PLUGIN" == "flannel" ]; then
        create_k3d_cluster "$CLUSTER_NAME_CONSUMER" "$here/manifests/k3d_consumer.yaml"
        create_k3d_cluster "$CLUSTER_NAME_PROVIDER" "$here/manifests/k3d_provider.yaml"
    else
        create_k3d_cluster "$CLUSTER_NAME_CONSUMER" "$here/manifests/k3d_consumer.yaml" "--flannel-backend=none@server:*" "--disable-network-policy@server:*"
        create_k3d_cluster "$CLUSTER_NAME_PROVIDER" "$here/manifests/k3d_provider.yaml" "--flannel-backend=none@server:*" "--disable-network-policy@server:*"
    fi

    # 3. Save the kubeconfig files
    K3D_KUBECONFIG_CONSUMER_LOCATION=$(get_k3d_kubeconfig $CLUSTER_NAME_CONSUMER)
    K3D_KUBECONFIG_PROVIDER_LOCATION=$(get_k3d_kubeconfig $CLUSTER_NAME_PROVIDER)

    cp "$K3D_KUBECONFIG_CONSUMER_LOCATION" "$here/$KUBECONFIG_CONSUMER"
    cp "$K3D_KUBECONFIG_PROVIDER_LOCATION" "$here/$KUBECONFIG_PROVIDER"

    # 4. Install the CNI (if needed)
    if [ "$CNI_PLUGIN" == "calico" ]; then
        create_resources "$KUBECONFIG_CONSUMER" "$MANIFEST_CALICO_1"
        create_resources "$KUBECONFIG_CONSUMER" "$MANIFEST_CALICO_2"
        create_resources "$KUBECONFIG_CONSUMER" "$MANIFEST_CALICO_3"

        create_resources "$KUBECONFIG_PROVIDER" "$MANIFEST_CALICO_1"
        create_resources "$KUBECONFIG_PROVIDER" "$MANIFEST_CALICO_2"
        create_resources "$KUBECONFIG_PROVIDER" "$MANIFEST_CALICO_3"
    fi

    # 5. Install Liqo
    install_liqo_k3d_version "$CLUSTER_NAME_CONSUMER" "$KUBECONFIG_CONSUMER" "$POD_CIDR" "$SERVICES_CIDR" "" "" "$here/manifests/liqo_consumer_values.yaml"
    install_liqo_k3d_version "$CLUSTER_NAME_PROVIDER" "$KUBECONFIG_PROVIDER" "$POD_CIDR" "$SERVICES_CIDR" "" "" ""
}


function setup_infrastructure() {
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


function validate_cli_inputs() {
    # Validating executor
    if [ -n "$K8S_EXECUTOR" ]; then
        case "$K8S_EXECUTOR" in
            "k3d")
                success "✔ Executor specified by argument: $K8S_EXECUTOR"
                ;;
            *)
                error "Invalid value for --executor. The only supported option is 'k3d'."
                exit 1
                ;;
        esac
    fi

    # Validating CNI
    if [ -n "$CNI_PLUGIN" ]; then
        case "$CNI_PLUGIN" in
            "flannel"|"calico")
                success "✔ CNI specified by argument: $CNI_PLUGIN"
                ;;
            *)
                error "Invalid value for --cni. Valid options are ${CNI_PLUGINS[*],,}."
                exit 1
                ;;
        esac
    fi
}


function main() {
    # Parse command-line arguments
    while [[ $# -gt 0 ]]; do
        key="$1"
        case $key in
            --executor)
            K8S_EXECUTOR=$2
            shift; shift 
            ;;
            --cni)
            CNI_PLUGIN=$2
            shift; shift
            ;;
            *)
            error "Unknown option: $1"
            exit 1
            ;;
        esac
    done

    clear

    echo -e "${YELLOW}=================================================${RESET}"
    echo -e "${YELLOW}===        Liqo Testbench Setup Script        ===${RESET}"
    echo -e "${YELLOW}=================================================${RESET}\n"

    # Validate CLI inputs
    validate_cli_inputs

    # If the options were not provided as arguments, ask the user
    if [ -z "$K8S_EXECUTOR" ]; then
        select_executor
    fi

    if [ -z "$CNI_PLUGIN" ]; then
        select_cni
    fi

    # Other interactive options
    # TODO: add to CLI inputs
    select_cache_option
    select_resources_option
    # TODO: select liqo version

    setup_k3d

    if [ "$RESOURCES_ENABLED" == "y" ]; then
        setup_infrastructure
    fi
}


main "$@"