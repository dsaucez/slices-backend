#!/usr/bin/env python3
import argparse
import argparse
import boto3
from botocore.client import Config
import json
import zipfile
import os
from git import Repo

import subprocess

def prepare_dir(experiment_id: str, credentials: str):
  dir=experiment_id

  os.makedirs(dir, exist_ok=True)

  return dir

def run_bash_command(command, working_dir="."):
    # Open a subprocess to execute the command
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=working_dir)
    
    # Stream the command output line-by-line to stdout
    while True:
        output = process.stdout.readline()
        if output == "" and process.poll() is not None:
            break
        if output:
            print(output.strip())

    # Wait for the command to complete and get the return code
    return_code = process.poll()
    if return_code != 0:
        # Optionally handle the error or capture stderr output
        error_output = process.stderr.read()
        print(f"Error: {error_output.strip()}")

def get_experiment(experiment_id: str, credentials: str, dir: str):
  repo_url = 'https://gitlab.inria.fr/slices-ri/blueprints/post-5g/reference_implementation.git'
  clone_to_dir = dir
  Repo.clone_from(repo_url, clone_to_dir, branch="develop")

  with open(credentials, 'r') as json_file:
    credentials = json.load(json_file)

    bucket=credentials["bucket"]

    s3 = boto3.resource('s3',
                        endpoint_url=credentials['endpointUrl'],
                        aws_access_key_id=credentials['accessKey'],
                        aws_secret_access_key=credentials['secretKey'],
                        config=Config(signature_version='s3v4'))

  s3_filename=f'{experiment_id}.zip'
  zip_file_path=f'{dir}/pos.zip'

  s3.Bucket(bucket).download_file(f"{s3_filename}", f'{zip_file_path}')

  if zipfile.is_zipfile(zip_file_path):
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
      zip_ref.extractall(dir)


def launch_experiment(experiment_id, credentials, dir: str):
  # Functionality to "launch" the experiment
  print(f"Launching experiment with ID: {experiment_id} using credentials from {credentials}")
  run_bash_command("pos/deploy.sh", working_dir=dir)

def main():
  parser = argparse.ArgumentParser(description='Experiment management commands.')
  parser.add_argument('command', choices=['experiment'], help='Command to execute.')
  parser.add_argument('action', choices=['get', 'launch'], help='Action to perform on the experiment.')
  parser.add_argument('experiment_id', help='ID of the experiment.')
  parser.add_argument('--credentials', default='credentials.json', help='Path to the credentials file.')

  args = parser.parse_args()

  dir = prepare_dir(experiment_id=args.experiment_id, credentials=args.credentials)

  if args.action == "get":
    get_experiment(experiment_id=args.experiment_id, credentials=args.credentials, dir=dir)
  elif args.action == "launch":
    launch_experiment(experiment_id=args.experiment_id, credentials=args.credentials, dir=dir)
  else:
    print("Invalid action. Use 'get' or 'launch'.")





if __name__ == "__main__":
  main()
