# Get the kubeconfig from parameter. If not provided, use default.
kubeconfig=${1:-~/.kube/config}

api_server_address=$(kubectl get nodes --kubeconfig "$kubeconfig" --selector=node-role.kubernetes.io/master -o jsonpath='{$.items[*].status.addresses[?(@.type=="InternalIP")].address}')

liqoctl install k3s --cluster-id milan --kubeconfig "$kubeconfig" --api-server-url "https://$api_server_address:6443" --pod-cidr "10.200.0.0/16" --service-cidr "10.71.0.0/16" --local-chart-path ../../../deployments/liqo --values ./values.yaml -v
