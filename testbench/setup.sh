#!/bin/bash

set -e

here="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# shellcheck source=/dev/null
source "$here/../../common.sh"
source "$here/utils.sh"


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

CILIUM_VALUES_FILE="$here/manifests/cilium_values.yaml"

K8S_ENVIRONMENTS=("k3d" "kind")
CNI_PLUGINS=("flannel" "calico" "cilium" "kindnet")

declare -A ENVIRONMENT_COMPATIBILITY
ENVIRONMENT_COMPATIBILITY[k3d]="flannel calico cilium"
ENVIRONMENT_COMPATIBILITY[kind]="kindnet"

declare -A GATEWAY_SERVICE_TYPE
GATEWAY_SERVICE_TYPE[k3d]="LoadBalancer"
GATEWAY_SERVICE_TYPE[kind]="NodePort"


K8S_ENVIRONMENT=""
CNI_PLUGIN=""
CACHE_ENABLED=""
RESOURCES_ENABLED=""
LIQO_REPO_URL=""
LIQO_COMMIT_ID=""

CONFIG_FILE="$here/.liqo_config"


function select_environment() {
    question "Select the Kubernetes environment"

    local options=("${K8S_ENVIRONMENTS[@]}" "Exit")
    PS3="Select the environment: "

    select opt in "${options[@]}"; do
        if [[ " ${K8S_ENVIRONMENTS[@]} " =~ " $opt " ]]; then
            K8S_ENVIRONMENT=$opt
            success "✔ Environment selected: $K8S_ENVIRONMENT"
            break
        elif [[ "$opt" == "Exit" ]]; then
            echo "Quitting."
            exit 0
        else
            error "Invalid option: $REPLY. Please try again."
        fi
    done
}


function select_cni() {
    question "Select the CNI to install"

    # Filter CNI options based on selected environment
    local compatible_cnis=(${ENVIRONMENT_COMPATIBILITY[$K8S_ENVIRONMENT]})

    local options=("${compatible_cnis[@]}" "Exit")
    PS3="Select the CNI: "

    select opt in "${options[@]}"; do
        if [[ " ${compatible_cnis[@]} " =~ " $opt " ]]; then
            CNI_PLUGIN=$opt
            success "✔ CNI selected: $CNI_PLUGIN"
            break
        elif [[ "$opt" == "Exit" ]]; then
            echo "Quitting."
            exit 0
        else
            error "Invalid option: $REPLY. Please try again."
        fi
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


function validate_environment() {
    if [[ ! " ${K8S_ENVIRONMENTS[@]} " =~ " $K8S_ENVIRONMENT " ]]; then
        error "Invalid Kubernetes environment: $K8S_ENVIRONMENT"
        exit 1
    fi
}


function validate_cni() {
    local compatible_cnis=(${ENVIRONMENT_COMPATIBILITY[$K8S_ENVIRONMENT]})

    if [[ ! " ${compatible_cnis[@]} " =~ " $CNI_PLUGIN " ]]; then
        error "CNI '$CNI_PLUGIN' is not compatible with environment '$K8S_ENVIRONMENT'."
        exit 1
    fi
}


function validate_boolean_option() {
    local option_value=$1
    local option_name=$2

    if [[ "$option_value" != "y" && "$option_value" != "n" ]]; then
        error "Invalid value for $option_name: $option_value. Valid options are 'y' or 'n'."
        exit 1
    fi
}


function select_liqo_version() {
    question "Do you want to specify a custom Liqo version?"

    read -p "Specify custom Liqo version? [y/N] " -n 1 -r
    echo
    REPLY=${REPLY,,}

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter Liqo repository URL: " LIQO_REPO_URL
        read -p "Enter Liqo commit ID: " LIQO_COMMIT_ID
        success "✔ Custom Liqo version configured (repo: $LIQO_REPO_URL, commit: $LIQO_COMMIT_ID)"
    else
        LIQO_REPO_URL=""
        LIQO_COMMIT_ID=""
        success "✔ Using default Liqo version"
    fi
}


function load_liqo_config() {
    if [ -f "$CONFIG_FILE" ]; then
        source "$CONFIG_FILE"
        if [ -n "$SAVED_LIQO_REPO_URL" ] || [ -n "$SAVED_LIQO_COMMIT_ID" ]; then
            info "Found saved Liqo configuration"
            return 0
        fi
    fi
    return 1
}


function save_liqo_config() {
    question "Do you want to save this Liqo version configuration for future use?"

    read -p "Save configuration? [y/N] " -n 1 -r
    echo
    REPLY=${REPLY,,}

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cat > "$CONFIG_FILE" <<EOF
# Liqo configuration file
SAVED_LIQO_REPO_URL="$LIQO_REPO_URL"
SAVED_LIQO_COMMIT_ID="$LIQO_COMMIT_ID"
EOF
        success "✔ Configuration saved to $CONFIG_FILE"
    else
        info "Configuration not saved"
    fi
}


function use_saved_liqo_config() {
    if load_liqo_config; then
        question "Use saved Liqo configuration?"
        echo "  Repository URL: ${SAVED_LIQO_REPO_URL:-<default>}"
        echo "  Commit ID: ${SAVED_LIQO_COMMIT_ID:-<default>}"
        
        read -p "Use saved configuration? [Y/n] " -n 1 -r
        echo
        REPLY=${REPLY,,}

        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            LIQO_REPO_URL="$SAVED_LIQO_REPO_URL"
            LIQO_COMMIT_ID="$SAVED_LIQO_COMMIT_ID"
            success "✔ Using saved Liqo configuration"
            return 0
        fi
    fi
    return 1
}


function setup_k3d() {
    # 1. Prepare the environment
    requirements=("k3d")
    if [ "$CNI_PLUGIN" == "cilium" ]; then
        requirements+=("cilium")
    fi
    check_requirements "${requirements[@]}"

    delete_k3d_clusters "$CLUSTER_NAME_CONSUMER" "$CLUSTER_NAME_PROVIDER"

    create_docker_network "virtual-cluster-k3d"

    # 2. Create the clusters
    options=()

    if [ "$CNI_PLUGIN" != "flannel" ]; then
        options+=("--k3s-arg" "--flannel-backend=none@server:*")
        options+=("--k3s-arg" "--disable-network-policy@server:*")
    fi

    if [ "$CACHE_ENABLED" == "y" ]; then
        connect_registry_proxy "virtual-cluster-k3d"

        local PROXY_HOST=$(get_container_ip "liqo_registry_proxy" "virtual-cluster-k3d")
        local PROXY_PORT=3128
        local REGISTRY_DIR="$here/../registry-proxy"

        options+=("--env" "HTTP_PROXY=http://$PROXY_HOST:$PROXY_PORT@all")
        options+=("--env" "HTTPS_PROXY=http://$PROXY_HOST:$PROXY_PORT@all")
        options+=("--env" "NO_PROXY=localhost,127.0.0.1,0.0.0.0,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,.local,.svc@all")
        options+=("--volume" "$REGISTRY_DIR/docker_mirror_certs/ca.crt:/etc/ssl/certs/registry-proxy-ca.pem")
    fi

    create_k3d_cluster "$CLUSTER_NAME_CONSUMER" "$here/manifests/k3d_consumer.yaml" "$options"
    create_k3d_cluster "$CLUSTER_NAME_PROVIDER" "$here/manifests/k3d_provider.yaml" "$options"

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

    if [ "$CNI_PLUGIN" == "cilium" ]; then
        install_cilium "$KUBECONFIG_CONSUMER" "$CILIUM_VALUES_FILE"
        install_cilium "$KUBECONFIG_PROVIDER" "$CILIUM_VALUES_FILE"
    fi

    # 5. Install Liqo
    install_liqo_k3d "$CLUSTER_NAME_CONSUMER" "$KUBECONFIG_CONSUMER" "$POD_CIDR" "$SERVICES_CIDR" "$LIQO_REPO_URL" "$LIQO_COMMIT_ID" ""
    install_liqo_k3d "$CLUSTER_NAME_PROVIDER" "$KUBECONFIG_PROVIDER" "$POD_CIDR" "$SERVICES_CIDR" "$LIQO_REPO_URL" "$LIQO_COMMIT_ID" ""
}


function setup_kind() {
    # 1. Prepare the environment
    check_requirements "kind"

    delete_clusters "$CLUSTER_NAME_CONSUMER" "$CLUSTER_NAME_PROVIDER"

    # 2. Create the clusters
    create_cluster "$CLUSTER_NAME_CONSUMER" "$KUBECONFIG_CONSUMER" "$here/manifests/kind_consumer.yaml"
    create_cluster "$CLUSTER_NAME_PROVIDER" "$KUBECONFIG_PROVIDER" "$here/manifests/kind_provider.yaml"

    # 3. Register image cache (if needed)
    if [ "$CACHE_ENABLED" == "y" ]; then
        connect_registry_proxy "kind"

        register_image_cache_kind "$CLUSTER_NAME_CONSUMER"
        register_image_cache_kind "$CLUSTER_NAME_PROVIDER"
    fi

    # 4. Install Liqo
    install_liqo_kind "$CLUSTER_NAME_CONSUMER" "$KUBECONFIG_CONSUMER" "$LIQO_COMMIT_ID" "$LIQO_REPO_URL"
    install_liqo_kind "$CLUSTER_NAME_PROVIDER" "$KUBECONFIG_PROVIDER" "$LIQO_COMMIT_ID" "$LIQO_REPO_URL"
}


function setup_infrastructure() {
    # 1. Peer the clusters
    peer_clusters "$KUBECONFIG_CONSUMER" "$KUBECONFIG_PROVIDER" "${GATEWAY_SERVICE_TYPE[$K8S_ENVIRONMENT]}"

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


function main() {
    # Parse command-line arguments
    while [[ $# -gt 0 ]]; do
        key="$1"
        case $key in
            --executor)
            K8S_ENVIRONMENT=$2
            shift; shift 
            ;;
            --cni)
            CNI_PLUGIN=$2
            shift; shift
            ;;
            --cache)
            CACHE_ENABLED=$2
            shift; shift
            ;;
            --resources)
            RESOURCES_ENABLED=$2
            shift; shift
            ;;
            --repo-url)
            LIQO_REPO_URL=$2
            shift; shift
            ;;
            --commit-id)
            LIQO_COMMIT_ID=$2
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

    if [ -z "$K8S_ENVIRONMENT" ]; then
        select_environment
    fi
    validate_environment

    if [ -z "$CNI_PLUGIN" ]; then
        select_cni
    fi
    validate_cni

    if [ -z "$CACHE_ENABLED" ]; then
        select_cache_option
    fi
    validate_boolean_option "$CACHE_ENABLED" "cache option"

    if [ -z "$RESOURCES_ENABLED" ]; then
        select_resources_option
    fi
    validate_boolean_option "$RESOURCES_ENABLED" "resources option"

    # Select Liqo version (only if not specified via command line)
    if [ -z "$LIQO_REPO_URL" ] && [ -z "$LIQO_COMMIT_ID" ]; then
        if ! use_saved_liqo_config; then
            select_liqo_version
        fi
        
        # Offer to save the configuration if it's custom
        if [ -n "$LIQO_REPO_URL" ] || [ -n "$LIQO_COMMIT_ID" ]; then
            save_liqo_config
        fi
    fi

    # Setup the clusters
    case $K8S_ENVIRONMENT in
        "k3d")
            setup_k3d
            ;;
        "kind")
            setup_kind
            ;;
        *)
            error "Unsupported Kubernetes environment: $K8S_ENVIRONMENT"
            exit 1
            ;;
    esac

    if [ "$RESOURCES_ENABLED" == "y" ]; then
        setup_infrastructure
    fi
}


main "$@"
