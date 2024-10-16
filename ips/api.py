from enum import Enum
from fastapi import FastAPI, HTTPException, Depends, Security, status, Response
from fastapi.security import APIKeyHeader
from pydantic import IPvAnyAddress, BaseModel, Field, field_validator
import traceback
from datetime import datetime, timedelta, timezone
import ip as iplib
from ipaddr import IPAddress, IPv4Network
import json
from typing import List
import itertools
from starlette.responses import StreamingResponse
from io import StringIO
from io import BytesIO
import zipfile
import boto3
from botocore.client import Config
import uuid
import paramiko
import os

import pos

# ===== CORS 
from fastapi.middleware.cors import CORSMiddleware
origins = [
    "http://mini-dmi.slices-staging.slices-be.eu",
    "https://mini-dmi.slices-staging.slices-be.eu",
    "http://localhost:8000",
    "https://localhost:8000",
    "http://localhost",
    "https://localhost",
    "http://172.29.7.10:8000",
    "https://172.29.7.10:8000",
    'http://post-5g-web.slices-ri.eu',
    'https://post-5g-web.slices-ri.eu',
    'http://duckburg.net.cit.tum.de',
    'https://duckburg.net.cit.tum.de'
]

# == API KEY ===================================================================
import jwt
api_key_header = APIKeyHeader(name="Bearer")

def get_s3_bucket():
    credentials = load_db(dbfile="/credentials.json")

    bucket=credentials["bucket"]

    s3 = boto3.resource('s3',
                        endpoint_url=credentials['endpointUrl'],
                        aws_access_key_id=credentials['accessKey'],
                        aws_secret_access_key=credentials['secretKey'],
                        config=Config(signature_version='s3v4'))

    bucket=credentials["bucket"]
    s3_bucket = s3.Bucket(bucket)
    return s3_bucket

def run_ssh_command_with_key(hostname, port, username, key_path, command):
    # Create a new SSH client
    ssh = paramiko.SSHClient()

    # Automatically add the host key if it's new
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Connect to the server using an SSH key
        # private_key = paramiko.RSAKey.from_private_key_file(key_path, password='Cu3skO2JawWLye6')
        # ssh.connect(hostname, port=port, username=username, pkey=private_key)
        ssh.connect(hostname, port=port, username=username, key_filename=key_path)

        # Execute the command
        stdin, stdout, stderr = ssh.exec_command(command)

        # Get the output and error
        output = stdout.read().decode()
        error = stderr.read().decode()

        return output, error
    finally:
        # Close the SSH connection
        ssh.close()

# def remove_expired():
#     for k, v in db["ips"].items():
#         ips  = v["reserved_ips"]

#         # get all expired IPs
#         expired = []
#         for ip, infos in ips.items():
#             if datetime.now(timezone.utc) > infos["expiration"]:
#                 expired.append(ip)

#         # purge the expired IPs
#         for ip in expired:
#             del ips[ip]

def check_role(allowed_roles: List[str]):
    """
    Creates a dependency that checks if the user has the required role(s).

    This function generates a role checker that validates whether the
    current user's role matches any of the allowed roles passed to the function.

    Args:
        allowed_roles (List[str]): A list of roles that are allowed access.

    Returns:
        function: A FastAPI dependency that checks user roles.

    Raises:
        HTTPException: If the user's role is not found among the allowed roles, 
        it raises a 403 Forbidden error.
    """
    def role_checker(info: dict = Depends(validate_token)):
        roles = [db["_roles"][role] for role in allowed_roles]
        users = list(set(itertools.chain(*roles)))
        if info["preferred_username"] not in users:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have the required role"
            )
        return info
    return role_checker

def validate_token(token: str = Security(api_key_header)):
    decoded = jwt.decode(token, options={'verify_signature': False})
    # TBD check that it is correct!!!
    
    # Check if not expired
    current_time = datetime.now(timezone.utc)
    if current_time > datetime.fromtimestamp(decoded['exp'], timezone.utc):
        raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
    return decoded
# ==============================================================================

def load_db(dbfile='/db.json'):
    """
    Loads and returns the content of a JSON database file.

    This function opens the specified JSON file and returns its content as a
    dictionary. If no file name is specified, it defaults to '/db.json'.

    Args:
        dbfile (str): The path to the JSON file to be loaded. Defaults to '/db.json'.

    Returns:
        dict: The database. 

    Raises:
        FileNotFoundError: If the specified file does not exist.
        json.JSONDecodeError: If the file contents cannot be decoded into valid JSON.
    """
    with open(dbfile, 'r') as json_file:
        loaded_db = json.load(json_file)
    return loaded_db

db = load_db()

ClusterNames = Enum('name', {cluster: cluster for cluster in db.keys()})

app = FastAPI(dependencies=[Depends(validate_token)])
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def expiration_time(delta=60):
    """
    Calculate the expiration time in UTC.

    This function computes the current UTC time and adds a specified 
    time delta (in seconds) to it. The default delta is set to 60 seconds.

    Args:
        delta (int, optional): The number of seconds to add to the current 
        UTC time. Defaults to 60.

    Returns:
        datetime: A timezone-aware `datetime` object representing the 
        current UTC time plus the specified delta.
    """
    current_utc_time = datetime.now(timezone.utc)
    later = current_utc_time + timedelta(seconds=delta)

    return later

# @app.delete("/ip/{cluster}/{ipaddress}")
# async def delete_ip(cluster: ClusterNames, ipaddress: IPvAnyAddress, user: dict = Depends(check_role(["admin"]))):
#     """
#     Delete a reserved IP address from a specified cluster.

#     This endpoint removes the specified IP address from the reserved IPs 
#     of the given cluster. If the IP address does not exist in the 
#     reserved list, a 404 error is returned.

#     Args:
#         cluster (ClusterNames): The name of the cluster from which the 
#         IP address is to be removed. Should match one of the defined 
#         cluster names.
        
#         ipaddress (IPvAnyAddress): The IP address to be removed. 
#         Must be a valid IPv4 or IPv6 address.

#     Raises:
#         HTTPException: If the IP address is not found in the reserved 
#         IPs of the specified cluster, a 404 error is raised with 
#         details about the failure.

#     Returns:
#         Dict[str, str]: A dictionary containing the removed IP address 
#         along with the associated cluster name.

#     Example:
#         DELETE /ip/my_cluster/192.168.1.10
#         Response:
#         {
#             "msg": "192.168.1.10 has been removed from cluster my_cluster",
#             "cluster": "my_cluster"
#         }

#         DELETE /ip/my_cluster/192.168.1.99
#         Response:
#         {
#             "msg": "Address not found",
#             "cluster": "my_cluster",
#             "ip": "192.168.1.99"
#         }
#     """
#     db_cluster = db["ips"][cluster.name]
#     reserved_ips = db_cluster["reserved_ips"]
#     try:
#         res = reserved_ips.pop(str(ipaddress))
#     except KeyError:
#         raise HTTPException(status_code=404, detail={"msg": "Address not found", "cluster": cluster.name, "ip": str(ipaddress)})
#     return res | {'cluster': cluster}

# @app.get("/ip/{cluster}")
# async def get_ip(cluster: ClusterNames, user: dict = Depends(check_role(["user"]))):
#     """
#     Reserve an IP address from a pool for a given cluster.

#     The reserved IP address and its expiration time are returned in the response.

#     Args:
#         cluster (ClusterNames): The name of the cluster from which to reserve an IP.

#     Returns:
#         dict: A dictionary containing the reserved IP address, its prefix length,
#         its expiration time, and the associated cluster name.

#     Raises:
#         HTTPException: If no available IP address can be reserved from the pool, 
#         a 404 error is raised.
#     """
#     cluster_name = cluster.name

#     try:
#         res = get_ip_in_cluster(cluster_name)
#     except ValueError as e:
#         raise HTTPException(status_code=404, detail=str(e))    

#     return res

# def _get_ip_in_cluster(cluster_name):
#     db_cluster = db["ips"][cluster_name]
#     reserved_ips = db_cluster["reserved_ips"]

#     pool = iplib.generate_ip_pool(db_cluster['prefix'])
#     prefix = IPv4Network(db_cluster['prefix'])

#     for ip, infos in reserved_ips.items():
#         pool.discard(infos["ip"])

#     reserved_ip = iplib.pick_and_remove_ip(pool)
    
#     entry= {
#         "ip": reserved_ip,
#         "prefixlen": prefix.prefixlen,
#         "expiration": expiration_time(delta=3600)
#         }
#     db_cluster['reserved_ips'][str(reserved_ip)] = entry
    
#     return entry | {"cluster": cluster_name}

@app.get("/db/")
async def get_db(user: dict = Depends(check_role(["admin"]))):
    return {"db": db}

@app.get("/reset/")
async def get_reset(user: dict = Depends(check_role(["admin"]))):
    global db
    db = load_db()
    return {"db": db}

@app.post("/pos/script/")
async def post_pos_script(data: pos.PosScriptData, user: dict = Depends(check_role(["user"]))):
    # Generate an ID
    id=data.experiment_id

    # deploy_node = data.deploy_node
    # url = data.xp_url

    # generate the inventory
    inventory = pos.generate_inventory(data=data, user=user, id=id)

    # generate the Ansible playbook
    playbook = pos.generate_playbook(data=data, user=user, id=id)

    # generate the Ansible playbook
    playbook_5g = pos.generate_playbook_5g(data=data, user=user, id=id)

    # generate the exectution script
    deploy = pos.generate_script(data=data, user=user, id=id)

    sh_5g = pos.generate_sh5g(data=data, user=user, id=id)


    # generate params parameters
    params = pos.generate_params(data=data, user=user, id=id)
    
    # generate params 5g parameters
    params5g = pos.generate_params5g(data=data, user=user, id=id)

    # generate dmi parameters
    dmi = pos.generate_dmi(data=data, user=user, id=id)

    xp = pos.generate_xp(data=data, user=user, id=id)

    # Create a Zip file with all content
    zip_buffer = BytesIO()
    # Add content to the zip file
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        zip_file.writestr("pos/deploy.sh", deploy)
        zip_info = zip_file.getinfo("pos/deploy.sh")
        zip_info.external_attr = 0o755 << 16

        zip_file.writestr("pos/5g.sh", sh_5g)
        zip_info = zip_file.getinfo("pos/5g.sh")
        zip_info.external_attr = 0o755 << 16

        zip_file.writestr("pos/provision.yaml", playbook)
        zip_file.writestr("pos/5g.yaml", playbook_5g)
        zip_file.writestr("pos/params.yaml", params)
        zip_file.writestr("pos/params.5g.yaml", params5g)
        zip_file.writestr("pos/params_dmi.yaml", dmi)
        zip_file.writestr("pos/hosts", inventory)

        zip_file.writestr("pos/get_xp.sh", xp)
        zip_info = zip_file.getinfo("pos/get_xp.sh")
        zip_info.external_attr = 0o755 << 16

    try:
        pos.generate_oai(data=data, user=user, id=id, zip_buffer=zip_buffer)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as err:
        full_traceback = traceback.format_exc()
        raise HTTPException(status_code=500, detail=str(full_traceback))

    zip_buffer.seek(0)

    s3_bucket = get_s3_bucket()
    s3_bucket.upload_fileobj(zip_buffer, f"{id}.zip")

    return {"identifier": id}

@app.get("/pos/script/{id}")
async def get_pos_script(id: str):
    try:
        s3_bucket = get_s3_bucket()

        dir = "xp"
        os.makedirs("xp", exist_ok=True)

        s3_filename=f'{id}.zip'
        tempfile_path = f'{dir}/{s3_filename}'

        s3_bucket.download_file(f"{s3_filename}", f'{tempfile_path}')

        # Open the file in binary mode
        file_like = open(tempfile_path, mode="rb")

        # Return the file as a streaming response
        return StreamingResponse(file_like, media_type="application/x-zip-compressed", 
                                    headers={"Content-Disposition": f"attachment; filename={s3_filename}"})
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        # remove the temporary file
        if os.path.exists(s3_filename):
            os.remove(s3_filename)



## R2LAB
r2lab_devices = ["jaguar", "panther", "n300", "n320", "qhat01"]
R2labDevices = Enum('name', {dev: dev for dev in r2lab_devices})

class StateUpdate(BaseModel):
    state: str = Field(..., description="State must be either 'ON' or 'OFF'")

    @field_validator('state')  
    def validate_state(cls, value):
        # Convert the input value to uppercase for case-insensitive comparison
        normalized_value = value.upper()
        if normalized_value not in ["ON", "OFF"]:
            raise ValueError("State must be either 'ON' or 'OFF'")
        return normalized_value

@app.patch("/r2lab/{device}/")
async def post_r2lab(state_update: StateUpdate, device: R2labDevices, user: dict = Depends(check_role(["user"]))):
    """
    Change the power state of a specified R2Lab device.

    This endpoint allows users to change the power state of a specific 
    R2Lab device to either ON or OFF.

    Parameters:
    - **state_update**: StateUpdate
        - Contains the state to set for the device. Must be either "ON" 
          or "OFF".
    - **device**: R2labDevices
        - The specific device in the R2Lab whose power state will be 
          modified.
    - **user**: dict
        - A dictionary representing the authenticated user, obtained 
          from the `check_role` dependency to ensure the user has the 
          correct permissions.

    Returns:
    - **JSON response** containing the output change in R2LAB structured as:
      ```json
      {
          "output": "<r2lab_output>"
      }
      ```

    Raises:
    - **HTTPException**: If an error occurs while executing the command, 
      the user will receive an appropriate HTTP error response.
    """
    normalized_state = state_update.state.upper()
    if normalized_state == "ON":
        cmd = f"rhubarbe pdu on {device.name}"
    elif normalized_state == "OFF":
        cmd = f"rhubarbe pdu off {device.name}"

    output, error = run_ssh_command_with_key("faraday.inria.fr", 22, "inria_tum01", "/id_rsa", cmd)

    return {"output": output}


@app.get("/prefix/")
async def get_prefix(user: dict = Depends(check_role(["admin", "user"]))):
    proj = user['proj']

    if proj not in db['cluster']['allocated'].keys():
        try:
            p = db['cluster']['subnets'].pop()
            db['cluster']['allocated'][proj] = p
        except IndexError:
            raise HTTPException(status_code=404, detail="No prefix is available")

        try:
            lb = db['metallb']['ips'].pop()
            db['metallb']['allocated'][proj] = lb
        except IndexError:
            raise HTTPException(status_code=404, detail="No LB IP is available")    
        

    else:
        p = db['cluster']['allocated'][proj]
        lb = db['metallb']['allocated'][proj]

    return {
        "subnet": p,
        "lb": lb
        }

@app.delete("/prefix/")
async def get_prefix(user: dict = Depends(check_role(["admin", "user"]))):
    proj = user['proj']

    if proj not in db['cluster']['allocated'].keys():
        raise HTTPException(status_code=404, detail="No prefix is allocated to your project")
    
    p = db['cluster']['allocated'][proj]
    db['cluster']['subnets'].append(p)

    lb = db['metallb']['allocated'][proj]
    db['metallb']['ips'].append(lb)

    del db['cluster']['allocated'][proj]
    del db['metallb']['allocated'][proj]

    return {"subnet": p,
            "lb": lb
            }