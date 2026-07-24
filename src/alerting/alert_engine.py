#!/usr/bin/env python3
"""
Cloud Alerting Engine
Monitors metrics and triggers alerts via SNS, Slack, and Email.

Author: Tushar Kumar
"""

import json
import logging
import time
import yaml
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    logger.error("Install: pip install requests pyyaml")


class AlertRule:
    """Defines an alerting rule"""
    def __init__(self, name, metric, threshold, operator, severity, duration=300):
        self.name = name
        self.metric = metric
        self.threshold = threshold
        self.operator = operator
        self.severity = severity
        self.duration = duration
        self.triggered_at = None

    def evaluate(self, current_value):
        ops = {'>': lambda a, b: a > b, '<': lambda a, b: a < b, '>=': lambda a, b: a >= b}
        return ops.get(self.operator, lambda a, b: False)(current_value, self.threshold)


class AlertingEngine:
    """Manages alert rules and notifications"""

    def __init__(self, config):
        self.config = config
        self.rules = []
        self.alert_history = []
        self.slack_webhook = config.get('slack_webhook_url')
        self.sns_topic_arn = config.get('sns_topic_arn')

        self._load_rules()

    def _load_rules(self):
        """Load alert rules from config"""
        rules_config = self.config.get('rules', [])
        for rule in rules_config:
            self.rules.append(AlertRule(
                name=rule['name'],
                metric=rule['metric'],
                threshold=rule['threshold'],
                operator=rule.get('operator', '>'),
                severity=rule.get('severity', 'WARNING'),
                duration=rule.get('duration', 300)
            ))
        logger.info(f"Loaded {len(self.rules)} alert rules")

    def evaluate_rules(self, metrics):
        """Evaluate all rules against current metrics"""
        for rule in self.rules:
            value = metrics.get(rule.metric)
            if value is not None and rule.evaluate(value):
                alert = {
                    'rule': rule.name,
                    'metric': rule.metric,
                    'current_value': value,
                    'threshold': rule.threshold,
                    'severity': rule.severity,
                    'timestamp': datetime.utcnow().isoformat()
                }
                self.alert_history.append(alert)
                self._send_notification(alert)
                logger.warning(f"ALERT: {rule.name} - {rule.metric}={value} {rule.operator} {rule.threshold}")

    def _send_notification(self, alert):
        """Send alert notification"""
        if self.slack_webhook:
            self._send_slack(alert)
        if self.sns_topic_arn:
            self._send_sns(alert)

    def _send_slack(self, alert):
        """Send Slack notification"""
        color = {'CRITICAL': '#ff0000', 'WARNING': '#ffaa00', 'INFO': '#36a64f'}.get(alert['severity'], '#36a64f')
        payload = {
            "attachments": [{
                "color": color,
                "title": f"🚨 {alert['severity']}: {alert['rule']}",
                "fields": [
                    {"title": "Metric", "value": alert['metric'], "short": True},
                    {"title": "Current Value", "value": str(alert['current_value']), "short": True},
                    {"title": "Threshold", "value": str(alert['threshold']), "short": True},
                    {"title": "Time", "value": alert['timestamp'], "short": True}
                ]
            }]
        }
        try:
            requests.post(self.slack_webhook, json=payload, timeout=10)
        except Exception as e:
            logger.error(f"Slack notification failed: {e}")

    def _send_sns(self, alert):
        """Send AWS SNS notification"""
        try:
            import boto3
            sns = boto3.client('sns')
            sns.publish(
                TopicArn=self.sns_topic_arn,
                Subject=f"[{alert['severity']}] {alert['rule']}",
                Message=json.dumps(alert, indent=2)
            )
        except Exception as e:
            logger.error(f"SNS notification failed: {e}")

    def get_alert_history(self, limit=50):
        """Get recent alert history"""
        return self.alert_history[-limit:]


def main():
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    engine = AlertingEngine(config.get('alerting', {}))

    # Simulated metrics (replace with actual Prometheus queries)
    while True:
        metrics = {
            'cpu_utilization': 85.5,
            'memory_usage': 72.3,
            'disk_usage': 91.2,
            'api_latency_ms': 450,
            'error_rate': 5.2
        }
        engine.evaluate_rules(metrics)
        time.sleep(60)


if __name__ == '__main__':
    main()
