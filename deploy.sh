#!/bin/bash

REGISTRY_ID="crp4q1r2fo7v9m0j1vvh"
SERVICE_ACCOUNT_ID="ajelb450lc8haab6f4u7"
SERVICES=("orchestrator")

echo "Logging into Yandex Container Registry..."
YC_TOKEN=$(yc iam create-token)
docker login cr.yandex -u iam -p $YC_TOKEN

for service in "${SERVICES[@]}"; do
  echo "Build $service..."

  cd $service

  docker build -t cr.yandex/$REGISTRY_ID/$service:latest .
  docker push cr.yandex/$REGISTRY_ID/$service:latest

  cd ..

  yc serverless container create --name $service 2>/dev/null || true

  echo "Deploying $service..."
  yc serverless container revision deploy \
      --container-name $service \
      --image cr.yandex/$REGISTRY_ID/$service:latest \
      --service-account-id $SERVICE_ACCOUNT_ID \
      --cores 1 \
      --memory 512MB \
      --concurrency 4

  echo "$service deployed successfully!"
done
