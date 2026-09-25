#!/usr/bin/env bash
# Build e deploy manual da Lambda process_car_parking.
# Uso: AWS_ACCOUNT_ID=<id da conta> [AWS_REGION=us-east-1] ./deploy.sh
set -euo pipefail

: "${AWS_ACCOUNT_ID:?defina AWS_ACCOUNT_ID}"
AWS_REGION="${AWS_REGION:-us-east-1}"
REGISTRY="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
ECR_REPOSITORY="process_car_parking-ecr-lambda"
FUNCTION_NAME="process_car_parking-lambda-processing"

cd "$(dirname "$0")"

aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$REGISTRY"
docker build -t "$REGISTRY/$ECR_REPOSITORY:latest" .
docker push "$REGISTRY/$ECR_REPOSITORY:latest"
aws lambda update-function-code --region "$AWS_REGION" --function-name "$FUNCTION_NAME" --image-uri "$REGISTRY/$ECR_REPOSITORY:latest"
