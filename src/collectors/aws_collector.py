#!/usr/bin/env python3
"""
AWS CloudWatch Metrics Collector
Collects metrics from AWS CloudWatch and exposes them as Prometheus metrics.

Author: Tushar Kumar
"""

import time
import logging
import yaml
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from prometheus_client import start_http_server, Gauge, Counter, Summary
    import boto3
except ImportError:
    logger.error("Install dependencies: pip install prometheus_client boto3 pyyaml")
    raise


# Prometheus Metrics
aws_ec2_cpu = Gauge('aws_ec2_cpu_utilization', 'EC2 CPU Utilization %', ['instance_id', 'instance_name', 'region'])
aws_ec2_network_in = Gauge('aws_ec2_network_in_bytes', 'EC2 Network In', ['instance_id', 'region'])
aws_ec2_network_out = Gauge('aws_ec2_network_out_bytes', 'EC2 Network Out', ['instance_id', 'region'])
aws_ec2_status = Gauge('aws_ec2_status_check', 'EC2 Status Check', ['instance_id', 'region'])
aws_s3_bucket_size = Gauge('aws_s3_bucket_size_bytes', 'S3 Bucket Size', ['bucket_name', 'region'])
aws_s3_requests = Counter('aws_s3_requests_total', 'S3 Requests', ['bucket_name', 'method'])
aws_rds_cpu = Gauge('aws_rds_cpu_utilization', 'RDS CPU Utilization %', ['db_instance', 'region'])
aws_rds_connections = Gauge('aws_rds_connections', 'RDS Active Connections', ['db_instance', 'region'])
aws_lambda_invocations = Counter('aws_lambda_invocations_total', 'Lambda Invocations', ['function_name', 'region'])
aws_lambda_errors = Counter('aws_lambda_errors_total', 'Lambda Errors', ['function_name', 'region'])
aws_lambda_duration = Summary('aws_lambda_duration_seconds', 'Lambda Duration', ['function_name', 'region'])
collector_scrape_duration = Summary('aws_collector_scrape_duration_seconds', 'Collector scrape duration')
collector_errors = Counter('aws_collector_errors_total', 'Collector errors')


class AWSCloudWatchCollector:
    """Collects AWS CloudWatch metrics and exports to Prometheus"""

    def __init__(self, config):
        self.region = config.get('region', 'ap-south-1')
        self.interval = config.get('interval', 60)
        self.ec2 = boto3.client('ec2', region_name=self.region)
        self.cloudwatch = boto3.client('cloudwatch', region_name=self.region)
        self.s3 = boto3.client('s3', region_name=self.region)
        self.lambda_client = boto3.client('lambda', region_name=self.region)
        logger.info(f"AWS Collector initialized for region: {self.region}")

    def get_metric(self, namespace, metric_name, dimensions, statistic='Average', period=300):
        """Fetch a single CloudWatch metric"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=10)

            response = self.cloudwatch.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                Dimensions=dimensions,
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=[statistic]
            )

            datapoints = response.get('Datapoints', [])
            if datapoints:
                return datapoints[-1].get(statistic, 0)
            return 0
        except Exception as e:
            logger.error(f"Error fetching {metric_name}: {e}")
            collector_errors.inc()
            return 0

    @collector_scrape_duration.time()
    def collect_ec2_metrics(self):
        """Collect EC2 instance metrics"""
        logger.info("Collecting EC2 metrics...")
        try:
            instances = self.ec2.describe_instances(
                Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
            )

            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    instance_id = instance['InstanceId']
                    instance_name = next(
                        (tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'),
                        instance_id
                    )
                    dims = [{'Name': 'InstanceId', 'Value': instance_id}]

                    # CPU Utilization
                    cpu = self.get_metric('AWS/EC2', 'CPUUtilization', dims)
                    aws_ec2_cpu.labels(instance_id=instance_id, instance_name=instance_name, region=self.region).set(cpu)

                    # Network In/Out
                    net_in = self.get_metric('AWS/EC2', 'NetworkIn', dims, 'Sum')
                    aws_ec2_network_in.labels(instance_id=instance_id, region=self.region).set(net_in)

                    net_out = self.get_metric('AWS/EC2', 'NetworkOut', dims, 'Sum')
                    aws_ec2_network_out.labels(instance_id=instance_id, region=self.region).set(net_out)

                    # Status Check
                    status = self.get_metric('AWS/EC2', 'StatusCheckFailed', dims, 'Maximum')
                    aws_ec2_status.labels(instance_id=instance_id, region=self.region).set(status)

                    logger.info(f"EC2 {instance_name}: CPU={cpu:.1f}%, NetIn={net_in}, NetOut={net_out}")

        except Exception as e:
            logger.error(f"Error collecting EC2 metrics: {e}")
            collector_errors.inc()

    def collect_s3_metrics(self):
        """Collect S3 bucket metrics"""
        logger.info("Collecting S3 metrics...")
        try:
            buckets = self.s3.list_buckets()
            for bucket in buckets['Buckets']:
                bucket_name = bucket['Name']
                dims = [{'Name': 'BucketName', 'Value': bucket_name}, {'Name': 'StorageType', 'Value': 'StandardStorage'}]

                size = self.get_metric('AWS/S3', 'BucketSizeBytes', dims, 'Average', 86400)
                aws_s3_bucket_size.labels(bucket_name=bucket_name, region=self.region).set(size)

        except Exception as e:
            logger.error(f"Error collecting S3 metrics: {e}")
            collector_errors.inc()

    def collect_lambda_metrics(self):
        """Collect Lambda function metrics"""
        logger.info("Collecting Lambda metrics...")
        try:
            functions = self.lambda_client.list_functions()
            for func in functions['Functions']:
                func_name = func['FunctionName']
                dims = [{'Name': 'FunctionName', 'Value': func_name}]

                invocations = self.get_metric('AWS/Lambda', 'Invocations', dims, 'Sum')
                if invocations > 0:
                    aws_lambda_invocations.labels(function_name=func_name, region=self.region).inc(invocations)

                errors = self.get_metric('AWS/Lambda', 'Errors', dims, 'Sum')
                if errors > 0:
                    aws_lambda_errors.labels(function_name=func_name, region=self.region).inc(errors)

        except Exception as e:
            logger.error(f"Error collecting Lambda metrics: {e}")
            collector_errors.inc()

    def run(self):
        """Main collection loop"""
        logger.info(f"Starting AWS collector (interval: {self.interval}s)")
        while True:
            try:
                self.collect_ec2_metrics()
                self.collect_s3_metrics()
                self.collect_lambda_metrics()
            except Exception as e:
                logger.error(f"Collection cycle error: {e}")
            time.sleep(self.interval)


def main():
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    aws_config = config.get('aws', {})
    port = aws_config.get('metrics_port', 9100)

    start_http_server(port)
    logger.info(f"Prometheus metrics server started on port {port}")

    collector = AWSCloudWatchCollector(aws_config)
    collector.run()


if __name__ == '__main__':
    main()
