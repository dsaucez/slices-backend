#!/usr/bin/bash
# Function to display usage with parameter explanations and example
usage() {
  echo "Usage: $0 --username <username> [--api-server-endpoint <api-server-endpoint>] [--cluster-name <cluster-name>] [--duration <duration>]"
  echo ""
  echo "Parameters:"
  echo "  --username             : (Required) The username to create in the cluster."
  echo "  --api-server-endpoint  : (Optional) The API server endpoint, must be in URL format (e.g., https://192.0.2.1:6443). Default is https://172.28.2.87:6443"
  echo "  --cluster-name         : (Optional) The name of the cluster you're targeting. Default is centralhub"
  echo "  --duration             : (Optional) The duration of the session in days. Must be a positive integer. Default is 7 days."
  echo ""
  echo "Example:"
  echo "$0 --username toto --api-server-endpoint https://192.0.2.1:6443 --cluster-name cluster --duration 7"
  exit 1
}

# Function to check if a value is an integer
is_integer() {
  [[ "$1" =~ ^[0-9]+$ ]]
}

# Set default value for duration
DURATION=7
CLUSTER_NAME=centralhub
API_SERVER_ENDPOINT=https://172.28.2.87:6443

# Check if the number of arguments is at least 2 (1 mandatory parameters and its value)
if [ "$#" -lt 2 ]; then
  usage
fi

# Parse the named parameters
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --username)
      USERNAME="$2"
      shift 2
      ;;
    --api-server-endpoint)
      API_SERVER_ENDPOINT="$2"
      shift 2
      ;;
    --cluster-name)
      CLUSTER_NAME="$2"
      shift 2
      ;;
    --duration)
      DURATION="$2"
      if ! is_integer "$DURATION"; then
        echo "Error: --duration must be an integer representing the number of days."
        usage
      fi
      shift 2
      ;;
    *)
      echo "Unknown parameter: $1"
      usage
      ;;
  esac
done

# Check if all required parameters are provided
if [[ -z "$USERNAME" || -z "$API_SERVER_ENDPOINT" || -z "$CLUSTER_NAME" ]]; then
  usage
fi

# Display the parameters (you can replace this part with your actual logic)
echo "Username: $USERNAME"
echo "API Server Endpoint: $API_SERVER_ENDPOINT"
echo "Cluster Name: $CLUSTER_NAME"


# If duration is provided, display it
if [[ -n "$DURATION" ]]; then
  echo "Duration: $DURATION days"
fi

GROUP=SLICES-RI

DIR=RBAC

USER_KEY=$DIR/$USERNAME/$USERNAME.key
USER_CSR=$DIR/$USERNAME/$USERNAME.csr
USER_CRT=$DIR/$USERNAME/$USERNAME.crt
K8S_SIGN_REQUEST=$DIR/$USERNAME/${USERNAME}_k8s_sign_request.yaml
KUBECONFIG=$DIR/$USERNAME/config-${USERNAME}

EXPIRATION_SECONDS=$(( $DURATION * 3600 * 24))

mkdir -p $DIR/$USERNAME

echo "Create private key"
openssl genrsa -out $USER_KEY 2048

echo "Create CSR"
openssl req -new -key $USER_KEY -out $USER_CSR -subj "/CN=$USERNAME/O=${GROUP}" #/O=kubeadm:cluster-admins"

request=$(cat $USER_CSR | base64 | tr -d "\n")

echo "Generate k8s sign request"
cat > $K8S_SIGN_REQUEST <<EOF
apiVersion: certificates.k8s.io/v1
kind: CertificateSigningRequest
metadata:
  name: $USERNAME
spec:
  request: $request
  signerName: kubernetes.io/kube-apiserver-client
  expirationSeconds: $EXPIRATION_SECONDS
  usages:
  - client auth
EOF

echo "Remove k8s sign request if present"
kubectl delete -f $K8S_SIGN_REQUEST || true

echo "Submit k8s sign request"
kubectl apply -f $K8S_SIGN_REQUEST

echo "Validate the request"
kubectl certificate approve $USERNAME

echo "Obtain the certificate"
kubectl get csr $USERNAME -o jsonpath='{.status.certificate}'| base64 -d > $USER_CRT

echo "Add user and context to kubeconfig"
cat << EOF > $KUBECONFIG
---
apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: $(cat /etc/kubernetes/pki/ca.crt | base64 | tr -d "\n") 
    server: $API_SERVER_ENDPOINT
  name: $CLUSTER_NAME
EOF

kubectl --kubeconfig=$KUBECONFIG config set-credentials $USERNAME --client-key=$USER_KEY --client-certificate=$USER_CRT --embed-certs=true
kubectl --kubeconfig=$KUBECONFIG config set-context $USERNAME --cluster=$CLUSTER_NAME --user=$USERNAME
kubectl --kubeconfig=$KUBECONFIG config use-context $USERNAME

K8SUSER=$USERNAME envsubst < bindings.yaml | kubectl create -f -