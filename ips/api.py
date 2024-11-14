from enum import Enum
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Security, status, Response, Request
from fastapi.security import APIKeyHeader
import logging
from uvicorn.config import LOGGING_CONFIG

from pydantic import IPvAnyAddress, BaseModel, Field, field_validator
import traceback
from datetime import datetime, timedelta, timezone
import ip as iplib
from ipaddr import IPAddress, IPv4Network
import json
from typing import List, Optional
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
import yaml

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
    'http://post-5g-web.slices-ri.eu',
    'https://post-5g-web.slices-ri.eu',
    'http://duckburg.net.cit.tum.de',
    'https://duckburg.net.cit.tum.de',
    'http://post5g-backend.slices-be.eu'
    'https://post5g-backend.slices-be.eu'
]

# == API KEY ===================================================================
import jwt
api_key_header = APIKeyHeader(name="Bearer", auto_error=False)

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
    logger = logging.getLogger("uvicorn.access")
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
    logger.info(token)
    logger.info(decoded)
    return decoded

# def validate_token(request: Request, token: str = Security(api_key_header)):
#     if request.url.path in ["/ns"]:
#         print ("skip")
#         return {}
#     decoded = jwt.decode(token, options={'verify_signature': False})
#     # TBD check that it is correct!!!
    
#     # Check if not expired
#     current_time = datetime.now(timezone.utc)
#     if current_time > datetime.fromtimestamp(decoded['exp'], timezone.utc):
#         raise HTTPException(
#                     status_code=status.HTTP_401_UNAUTHORIZED,
#                     detail="Token has expired",
#                     headers={"WWW-Authenticate": "Bearer"},
#                 )
#     return decoded

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

# LOGGING_CONFIG["formatters"]["access"]["fmt"] = "%(asctime)s - %(levelname)s - %(client_addr)s - %(request_line)s - %(status_code)s"
# LOGGING_CONFIG["formatters"]["access"]["datefmt"] = "%Y-%m-%d %H:%M:%S"

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": "/logs/access.log",
            "when": "midnight",          # Rotate daily at midnight
            "interval": 1,               # Rotate every 1 day
            "backupCount": 7,            # Keep last 7 days of logs
            "formatter": "default",
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },
    "loggers": {
        "uvicorn.access": {  # Uvicorn's access logger
            "level": "INFO",
            "handlers": ["file", "console"],
            "propagate": False,
        },
        "uvicorn.error": {  # Uvicorn's error logger
            "level": "INFO",
            "handlers": ["file", "console"],
            "propagate": False,
        },
        "my_app_logger": {  # Custom application logger
            "level": "INFO",
            "handlers": ["file", "console"],
            "propagate": False,
        },
    },
}


# Apply the updated configuration
logging.config.dictConfig(LOGGING_CONFIG)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run on startup

    yield  # This yields control to the app during its run

    # Code to run on shutdown
    await shutdown_method()  # Replace with your specific shutdown method

async def shutdown_method():
    with open("/db.json", "w") as file:
        json.dump(db, file, indent=4)

app.router.lifespan_context = lifespan

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

@app.get("/db/")
async def get_db(user: dict = Depends(check_role(["admin"]))):
    """
    GET /db/ endpoint to retrieve the database object. Only accessible to users with the "admin" role.

    Parameters:
    user (dict): Authenticated user information.

    Returns:
    dict: A dictionary containing all database entries.

    Raises:
    HTTPException: If the user does not have the "admin" role, an HTTPException with a 403 status code
                   will be raised to deny access.
    """
    return {"db": db}

@app.get("/reset/")
async def get_reset(user: dict = Depends(check_role(["admin"]))):
    """
    GET /reset/ endpoint to reset the database by reloading it. Only accessible to users with the "admin" role.

    This function resets the database.

    Parameters:
    user (dict): Authenticated user information.

    Returns:
    dict: A dictionary containing the reloaded database.

    Raises:
    HTTPException: If the user does not have the "admin" role, an HTTPException with a 403 status code
                   will be raised to deny access.
    """
    global db
    db = load_db()
    return {"db": db}

@app.post("/pos/script/")
async def post_pos_script(data: pos.PosScriptData, user: dict = Depends(validate_token)):
# async def post_pos_script(data: pos.PosScriptData, user: dict = Depends(check_role(["user"]))):
    # Generate an ID
    id=data.experiment_id

    # Prefix the namespaces to belong to the user
    nsprefix=user['preferred_username']
    if "namespace" in data.params_5g['GCN']['core']:
        data.params_5g['GCN']['core']['namespace'] = "{}-{}".format(nsprefix, data.params_5g['GCN']['core']['namespace'])

    if "namespace" in data.params_5g['GCN']['RAN']:
        data.params_5g['GCN']['RAN']['namespace'] = "{}-{}".format(nsprefix, data.params_5g['GCN']['RAN']['namespace'])

    if "namespace" in data.params_5g['GCN']['UE']:
        data.params_5g['GCN']['UE']['namespace'] = "{}-{}".format(nsprefix, data.params_5g['GCN']['UE']['namespace'])

    # Create a Zip file with all content
    zip_buffer = BytesIO()

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
    
    # generate OAI configuration
    try:
        pos.generate_oai(data=data, user=user, id=id, zip_buffer=zip_buffer)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as err:
        full_traceback = traceback.format_exc()
        raise HTTPException(status_code=500, detail=str(full_traceback))
    
    # generate params 5g parameters
    params5g = pos.generate_params5g(data=data, user=user, id=id)

    # generate dmi parameters
    dmi = pos.generate_dmi(data=data, user=user, id=id)

    xp = pos.generate_xp(data=data, user=user, id=id)

    # Add content to the zip file
    with zipfile.ZipFile(zip_buffer, "a") as zip_file:
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

    zip_buffer.seek(0)

    s3_bucket = get_s3_bucket()
    s3_bucket.upload_fileobj(zip_buffer, f"{id}.zip")

    return {"identifier": id}

@app.get("/pos/script/{id}")
async def get_pos_script(id: str, user: dict = Depends(validate_token)):
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
async def post_r2lab(state_update: StateUpdate, device: R2labDevices, user: dict = Depends(validate_token)):
    """
    PATCH /r2lab/{device}/ endpoint to update the state of an R2lab device. The state can be set to `"ON"` or `"OFF"`.

    Parameters:
    state_update (StateUpdate): A dictionnary wich key `state` contains the
                                updated state for the device. The state is
                                either `"ON"` or `"OFF"`, and is normalized to
                                uppercase.
    device (R2labDevices): The name of the R2lab device whose state is being
                           updated.
    user (dict): Authenticated user information.

    Returns:
    dict: A dictionary containing the output of the power state update.

    Raises:
    ValueError: If the state is neither `"ON"` nor `"OFF"`.

    Note:
    The public key to use to connect to R2LAB is read from `/id_rsa`.
    """
    normalized_state = state_update.state.upper()
    if normalized_state == "ON":
        cmd = f"rhubarbe pdu on {device.name}"
    elif normalized_state == "OFF":
        cmd = f"rhubarbe pdu off {device.name}"

    output, error = run_ssh_command_with_key("faraday.inria.fr", 22, "inria_tum01", "/id_rsa", cmd)

    return {"output": output}


# Pydantic model to define the expected POST body structure
class TokenRequest(BaseModel):
    token: str
    class Config:
        json_schema_extra = {
            "example": {
                "token": "an experiment token, generated with, e.g., `slices experiment jwt <experiment name>`"
            }
        }

@app.post("/prefix/")
async def post_prefix(request_body: TokenRequest, user: dict = Depends(validate_token)):
    """
    POST /prefix/ endpoint to retrieve the subnet and load balancer (LB) IP
    allocated to the experiment associated with the user. If no resources have
    been allocated yet, it attempts to allocate a new subnet and LB IP. 
    This endpoint accepts a JSON body containing an experiment JWT token (e.g.,
    generated with `slices experiment jwt <experiment name>`).


    Parameters:
    request_body (TokenRequest): The body of the POST request containing the JWT
                                experiment token.
    user (dict): Authenticated user information.

    Returns:
    dict: A dictionary containing the allocated subnet (key `subnet`) and load
    balancer IP (key `lb`) for the user's experiment.

    
    Example Request body example (JSON):
    ```
    {
        "token": "your_jwt_token_here"
    }
    ```

    Example Response:
    ```
    {
        "subnet": "192.0.2.0/24",
        "lb": "198.51.100.1"
    }
    ```

    Behavior:
    - If the experiment does not already have an allocated subnet and LB IP:
      - A subnet is taken from `db['cluster']['subnets']` and assigned to the experiment.
      - A load balancer IP is popped from `db['metallb']['ips']` and assigned to the experiment.
    - If the experiment already has allocated resources, they are returned without allocating new ones.

    Raises:
    HTTPException: 
    - 404 if there are no available subnets to allocate.
    - 404 if there are no available LB IPs to allocate.

    Notes:
    - The `db` object is expected to contain two key parts:
      - `db['cluster']['subnets']`: A list of available subnets.
      - `db['metallb']['ips']`: A list of available load balancer IPs.
    - The function ensures resources are allocated only once per experiment.

    """
    # exp = user['proj']

    token = request_body.token
    try:
        data = validate_token(token)
        exp = data['sub']
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Experiment token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid experiment token")

    if exp not in db['cluster']['allocated'].keys():
        try:
            p = db['cluster']['subnets'].pop()
            db['cluster']['allocated'][exp] = p
        except IndexError:
            raise HTTPException(status_code=404, detail="No prefix is available")

        try:
            lb = db['metallb']['ips'].pop()
            db['metallb']['allocated'][exp] = lb
        except IndexError:
            raise HTTPException(status_code=404, detail="No LB IP is available")    
        

    else:
        p = db['cluster']['allocated'][exp]
        lb = db['metallb']['allocated'][exp]

    return {
        "subnet": p,
        "lb": lb
        }

@app.delete("/prefix/")
async def get_prefix(request_body: TokenRequest, user: dict = Depends(validate_token)):
    """
    DELETE /prefix/ endpoint to release the subnet and load balancer (LB) IP
    allocated to the user's project. The released resources are returned to
    their respective pools. This endpoint accepts a JSON body containing an
    experiment JWT token (e.g., generated with
    `slices experiment jwt <experiment name>`).

    Parameters:
    request_body (TokenRequest): The body of the DELETE request containing the JWT
                                 experiment token.
    user (dict): Authenticated user information.

    Returns:
    dict: A dictionary containing the released subnet (key `subnet`) and load
    balancer IP (key `lb`) for the user's project.

    Example Request body example (JSON):
    ```
    {
        "token": "your_jwt_token_here"
    }
    ```
    Example Response:
    ```
    {
        "subnet": "192.0.2.0/24",
        "lb": "198.51.100.1"
    }
    ```

    Raises:
    HTTPException: 
    - 404 if no subnet or LB IP is allocated to the user's project.
    """
    proj = user['proj']

    token = request_body.token
    try:
        data = validate_token(token)
        exp = data['sub']
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Experiment token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid experiment token")


    if exp not in db['cluster']['allocated'].keys():
        raise HTTPException(status_code=404, detail="No prefix is allocated to your project")
    
    p = db['cluster']['allocated'][exp]
    db['cluster']['subnets'].append(p)

    lb = db['metallb']['allocated'][exp]
    db['metallb']['ips'].append(lb)

    del db['cluster']['allocated'][exp]
    del db['metallb']['allocated'][exp]

    return {"subnet": p,
            "lb": lb
            }


def string_streamer(data: str):
    """Generator function to yield parts of a string."""
    for char in data:
        yield char

@app.post("/k8s/{cluster}")
async def post_kubeconfig(cluster: Optional[str] = "centralhub", user: dict = Depends(validate_token)):
    """
    POST /k8s/{cluster}/ endpoint to retrieve and return the kubeconfig file for a specific Kubernetes cluster.

    Parameters:
    -----------
    cluster : Optional[str], default="centralhub"
        The name of the Kubernetes cluster to target. If not provided, it defaults to "centralhub".

    user (dict): Authenticated user information.

    Returns:
    --------
    StreamingResponse:
        A streaming response that yields the kubeconfig in YAML format. The response is of MIME type `application/x-yaml`.

    Raises:
    -------
    HTTPException: 
    - 404 if the cluster does not exist.
    """
    if cluster == "centralhub":
        cmd = "cd users; ./add.sh {}".format(user['preferred_username'])
        output, error = run_ssh_command_with_key("172.29.0.11", 22, "backend", "/id_rsa", cmd)
        config = yaml.safe_load(output)
    else:
        raise HTTPException(status_code=404, detail="The cluster doesn't exist")

    return StreamingResponse(string_streamer(yaml.dump(config)), media_type="application/x-yaml")




# @app.post("/ns")
# async def post_ns(request: Request):
#     body = await request.json()
#     print (body)root@post5g-backend:~# 