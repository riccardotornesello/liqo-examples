# Use now
kubectl --kubeconfig liqo_kubeconf_milan -n liqo-tenant-rome exec --stdin --tty gw-milan-7858fb6ddd-mksp5 --container gateway -- nft list ruleset > out/milan-gateway-nft

# Get important resources
bash scripts/export-all-ns.sh firewallconfiguration
bash scripts/export-all-ns.sh routeconfiguration
bash scripts/export-all-ns.sh network
bash scripts/export-all-ns.sh ip
bash scripts/export-all-ns.sh genevetunnel
bash scripts/export-all-ns.sh internalfabric
bash scripts/export-all-ns.sh internalnode

# Get nftables ruleset
docker exec -it rome-control-plane nft list ruleset > out/nft-rome-control-plane
kubectl --kubeconfig liqo_kubeconf_rome -n liqo-tenant-milan exec --stdin --tty gw-milan-7858fb6ddd-mksp5 --container gateway -- nft list ruleset > out/nft-gateway
kubectl --kubeconfig liqo_kubeconf_rome -n rome-local exec --stdin --tty p1 -- nft list ruleset > out/nft-p1
kubectl --kubeconfig liqo_kubeconf_rome -n rome-offloaded exec --stdin --tty p2 -- nft list ruleset > out/nft-p2

# Get routes
docker exec -it rome-control-plane ip route list table all > out/routes-rome-control-plane
kubectl --kubeconfig liqo_kubeconf_rome -n liqo-tenant-milan exec --stdin --tty gw-milan-7858fb6ddd-mksp5 --container gateway -- ip route list table all > out/routes-gateway
kubectl --kubeconfig liqo_kubeconf_rome -n rome-local exec --stdin --tty p1 -- ip route list table all > out/routes-p1
kubectl --kubeconfig liqo_kubeconf_rome -n rome-offloaded exec --stdin --tty p2 -- ip route list table all > out/routes-p2

# Get interfaces
docker exec -it rome-control-plane ip a > out/interfaces-rome-control-plane
kubectl --kubeconfig liqo_kubeconf_rome -n liqo-tenant-milan exec --stdin --tty gw-milan-7858fb6ddd-mksp5 --container gateway -- ip a > out/interfaces-gateway
kubectl --kubeconfig liqo_kubeconf_rome -n rome-local exec --stdin --tty p1 -- ip a > out/interfaces-p1
kubectl --kubeconfig liqo_kubeconf_rome -n rome-offloaded exec --stdin --tty p2 -- ip a > out/interfaces-p2

# Add firewall rule
kubectl --kubeconfig liqo_kubeconf_milan create namespace test
kubectl --kubeconfig liqo_kubeconf_milan apply -f myrule.yaml

python3 test-network/test2.py

kubectl --kubeconfig liqo_kubeconf_rome apply -f newpod.yaml

kubectl --kubeconfig liqo_kubeconf_milan apply -f mynetpol.yaml

ATTENZIONE!!!!!!!!!!!!!!!!!!!!!!!!!
SE CANCELLO LA REGOLA CONTINUA A FUNZIONARE

# Build Webhook
DOCKER_ORGANIZATION=riccardotornesello DOCKER_TAG=v7 ARCHS=linux/amd64 DOCKER_REGISTRY=ttl.sh bash build/liqo/build.sh ./cmd/webhook/
kubectl --kubeconfig examples/riccardo/liqo_kubeconf_rome -n liqo set image deployment/liqo-webhook webhook=ttl.sh/riccardotornesello/webhook-ci:v7
kubectl --kubeconfig examples/riccardo/liqo_kubeconf_rome get pods -A

kubectl --kubeconfig examples/riccardo/liqo_kubeconf_rome apply -f examples/riccardo/mybrokenrule.yaml

kubectl --kubeconfig examples/riccardo/liqo_kubeconf_rome -n liqo logs liqo-webhook-7cbf7978b4-x4lb8