#!/bin/bash

REGISTRY_ID="crp4q1r2fo7v9m0j1vvh"
SERVICE_ACCOUNT_ID="ajelb450lc8haab6f4u7"
SERVICES=("rag_service" "orchestrator" "tgbot_service" "validator" "yandexgpt_service")
extract_url() {
    local data="$1"
    echo "$data" | grep -oP 'url:\s*\K[^[:space:]]+'
}

get_container_url() {
    local container_name="$1"
    local data
    data=$(yc serverless container get "$container_name" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        extract_url "$data"
    else
        echo ""
    fi
}

echo "Logging into Yandex Container Registry..."
YC_TOKEN=$(yc iam create-token)
docker login cr.yandex -u iam -p $YC_TOKEN

for service in "${SERVICES[@]}"; do
    container_name="${service//_/-}"

    if ! yc serverless container get --name $container_name &>/dev/null; then
        echo "Creating container $container_name..."
        yc serverless container create --name $container_name
    else
        echo "Container $container_name already exists"
    fi
done

declare -A container_urls
for service in "${SERVICES[@]}"; do
    container_name="${service//_/-}"
    echo "Getting URL for $container_name..."
    
    url=$(get_container_url "$container_name")
    url="${url%?}"
    if [ -n "$url" ]; then
        container_urls["$service"]=$url
        echo "$container_name URL: $url"
    else
        echo "URL not found for $container_name"
        container_urls["$service"]=""
    fi
done

for service in "${SERVICES[@]}"; do
    echo "Building $service..."
    
    cd $service
    docker build -t cr.yandex/$REGISTRY_ID/$service:latest .
    docker push cr.yandex/$REGISTRY_ID/$service:latest
    cd ..
    
    container_name="${service//_/-}"
    
    deploy_cmd="yc serverless container revision deploy \
        --container-name $container_name \
        --image cr.yandex/$REGISTRY_ID/$service:latest \
        --service-account-id $SERVICE_ACCOUNT_ID \
        --execution-timeout 3m \
        --cores 1 \
        --concurrency 4 \
        --environment FOLDER_ID=$FOLDER_ID \
        --memory=512MB"
    
    case $service in
        "orchestrator")
            if [ -n "${container_urls[yandexgpt_service]}" ]; then
                deploy_cmd="$deploy_cmd --environment LLM_URL=${container_urls[yandexgpt_service]}"
            fi
            if [ -n "${container_urls[validator]}" ]; then
                deploy_cmd="$deploy_cmd --environment VALIDATOR_URL=${container_urls[validator]}"
            fi
            if [ -n "${container_urls[rag_service]}" ]; then
                deploy_cmd="$deploy_cmd --environment RAG_URL=${container_urls[rag_service]}"
            fi
            ;;
        "tgbot_service")
            deploy_cmd="$deploy_cmd --min-instances=1"  
            if [ -n "${container_urls[orchestrator]}" ]; then
                deploy_cmd="$deploy_cmd --environment ORCHESTRATOR_URL=${container_urls[orchestrator]}"
            fi
            if [ -n "${container_urls[tgbot_service]}" ]; then
                deploy_cmd="$deploy_cmd --environment WEBHOOK_URL=${container_urls[tgbot_service]}"
            fi
            ;;
        "validator")
            if [ -n "${container_urls[orchestrator]}" ]; then
                deploy_cmd="$deploy_cmd --environment ORCHESTRATOR_URL=${container_urls[orchestrator]}"
            fi
            if [ -n "${container_urls[yandexgpt_service]}" ]; then
                deploy_cmd="$deploy_cmd --environment LLM_URL=${container_urls[yandexgpt_service]}"
            fi
            ;;
        "rag_service")
            deploy_cmd="$deploy_cmd --min-instances=1"
            if [ -n "${container_urls[orchestrator]}" ]; then
                deploy_cmd="$deploy_cmd --environment ORCHESTRATOR_URL=${container_urls[orchestrator]}"
            fi
            deploy_cmd="$deploy_cmd --memory=2048MB"
            ;;
        "yandexgpt_service")
            if [ -n "${container_urls[orchestrator]}" ]; then
                deploy_cmd="$deploy_cmd --environment ORCHESTRATOR_URL=${container_urls[orchestrator]}"
            fi
            ;;
    esac
    
    echo "Deploying $service..."
    eval $deploy_cmd
    
    final_url=$(get_container_url "$container_name")
    if [ -n "$final_url" ]; then
        echo "$service deployed successfully! URL: $final_url"
    else
        echo "$service deployed successfully! (URL not available yet)"
    fi
done

echo ""
echo "All services deployed!"
echo "Final URLs:"
for service in "${SERVICES[@]}"; do
    container_name="${service//_/-}"
    url=$(get_container_url "$container_name")
    if [ -n "$url" ]; then
        echo "   $container_name: $url"
    else
        echo "   $container_name: URL not available"
    fi
done