# 📊 Cloud Monitoring & Alerting Dashboard

![AWS CloudWatch](https://img.shields.io/badge/AWS-CloudWatch-orange?logo=amazonaws)
![Azure Monitor](https://img.shields.io/badge/Azure-Monitor-blue?logo=microsoftazure)
![Grafana](https://img.shields.io/badge/Grafana-Dashboards-F46800?logo=grafana)
![Prometheus](https://img.shields.io/badge/Prometheus-Metrics-E6522C?logo=prometheus)
![Python](https://img.shields.io/badge/Python-3.11+-yellow?logo=python)

## 📋 Overview

A unified **multi-cloud monitoring dashboard** that aggregates metrics from **AWS CloudWatch**, **Azure Monitor**, and **GCP Cloud Monitoring** into a single pane of glass. Features real-time dashboards, custom alerting with automated incident response, log aggregation, and serverless automation using AWS Lambda/Azure Functions.

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Grafana Dashboard Layer                     │
│         (Unified Visualization & Alerting UI)                 │
├──────────────────────────────────────────────────────────────┤
│                    Prometheus (Metrics Store)                 │
│              (Time-series DB + Alert Manager)                 │
├───────────┬──────────────────┬───────────────────────────────┤
│  AWS      │     Azure        │          GCP                  │
│  Collector│    Collector     │       Collector                │
├───────────┼──────────────────┼───────────────────────────────┤
│ CloudWatch│  Azure Monitor   │   Cloud Monitoring             │
│ + CW Logs │  + Log Analytics │   + Cloud Logging              │
└───────────┴──────────────────┴───────────────────────────────┘
         │              │                │
         └──────────────┴────────────────┘
              Alert Manager → SNS/Lambda
              (Auto-Remediation)
```

## 🚀 Quick Start

```bash
# Clone the repo
git clone https://github.com/sparrow000iv/cloud-monitoring-dashboard.git
cd cloud-monitoring-dashboard

# Install dependencies
pip install -r requirements.txt

# Configure cloud credentials
cp config/config.example.yaml config/config.yaml
# Edit config.yaml with your cloud credentials

# Start monitoring collectors
python src/collectors/aws_collector.py &
python src/collectors/azure_collector.py &
python src/collectors/gcp_collector.py &

# Start Prometheus + Grafana
docker-compose up -d
```

## 📊 Dashboard Features

- **CPU/Memory/Network** utilization across all cloud instances
- **API Latency** monitoring for REST endpoints
- **Custom Alerts** with Slack/Email/SNS notifications
- **Log Aggregation** pipeline for troubleshooting
- **Cost Monitoring** dashboards

## 👤 Author
**Tushar Kumar** — [GitHub](https://github.com/sparrow000iv) | [LinkedIn](https://www.linkedin.com/in/tushar-kumar-737a6b303/)
