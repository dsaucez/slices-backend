#!/usr/bin/env python3
import argparse
import boto3
from botocore.client import Config
import json
import os

def get_experiment(experiment: str, credentials: str):
  with open(credentials, 'r') as json_file:
    credentials = json.load(json_file)

    bucket=credentials["bucket"]

    s3 = boto3.resource('s3',
                        endpoint_url=credentials['endpointUrl'],
                        aws_access_key_id=credentials['accessKey'],
                        aws_secret_access_key=credentials['secretKey'],
                        config=Config(signature_version='s3v4'))

  os.makedirs(experiment, exist_ok=True)
  s3.Bucket(bucket).download_file(f"{experiment}.zip", f'{experiment}/pos.zip')

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Get experiment scripts.")
  
  parser.add_argument('experiment', type=str, help="Name of the experiment to retrieve")
  parser.add_argument('--credentials', type=str, help="Credentials file for accessing S3 storage", default='credentials.json')

  args = parser.parse_args()

  get_experiment(experiment=args.experiment, credentials=args.credentials)


