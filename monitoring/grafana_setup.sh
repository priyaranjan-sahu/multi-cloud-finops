#!/bin/bash

echo "Setting up Grafana for real-time cost monitoring..."

# Install Grafana
sudo apt update
sudo apt install -y grafana

# Start Grafana
sudo systemctl start grafana-server
sudo systemctl enable grafana-server

echo "Grafana is now running at http://localhost:3000"
