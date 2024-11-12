#!/usr/bin/bash

# Check if a user argument is provided
if [ -z "$1" ]; then
  echo "Error: No user specified."
  exit 1
fi

# Assign the first argument to the variable 'user'
user="$1"

# Define the directory path
dir="RBAC/$user"
config_file="$dir/config-$user"

# Check if the directory exists
if [ -d "$dir" ]; then
  # If the directory exists, check if the config-user file exists and output its content
  if [ ! -f "$config_file" ]; then
    echo "Error: $config_file does not exist."
    exit 1
  fi
else
  # If the directory doesn't exist, create the user
  ./add_user.sh --username $user 1>&2
fi
cat $config_file

d=$(date +%s)
mkdir $d
mv $dir $d
tar -uf rbac.tar $d
rm -r $d