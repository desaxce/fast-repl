#!/bin/bash

echo "Starting Docker cleanup process..."

# Remove all stopped containers
echo "Removing stopped containers..."
docker container prune -f

# Remove unused images
echo "Removing dangling images..."
docker image prune -f

# Remove unused volumes
echo "Removing unused volumes..."
docker volume prune -f

# Remove unused networks
echo "Removing unused networks..."
docker network prune -f

# Get space reclaimed
echo "Checking current Docker disk usage..."
docker system df

# For a more aggressive cleanup, uncomment these lines:
# echo "Removing all unused images (not just dangling ones)..."
# docker image prune -a -f

# echo "Performing a full system prune..."
# docker system prune -a -f --volumes

echo "Docker cleanup completed!"
