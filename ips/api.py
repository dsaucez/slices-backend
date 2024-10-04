from enum import Enum
from fastapi import FastAPI, HTTPException, Depends, Security, status, Response
from fastapi.security import APIKeyHeader
from pydantic import IPvAnyAddress
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


import pos

# == API KEY ===================================================================
import jwt
api_key_header = APIKeyHeader(name="Bearer")

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

def expiration_time(delta=1):
    """
    Calculate the expiration time in UTC.

    This function computes the current UTC time and adds a specified 
    time delta (in hours) to it. The default delta is set to 1 hour.

    Args:
        delta (int, optional): The number of hours to add to the current 
        UTC time. Defaults to 1.

    Returns:
        datetime: A timezone-aware `datetime` object representing the 
        current UTC time plus the specified delta.
    """
    current_utc_time = datetime.now(timezone.utc)
    one_hour_later = current_utc_time + timedelta(hours=delta)

    return one_hour_later

@app.delete("/ip/{cluster}/{ipaddress}")
async def delete_ip(cluster: ClusterNames, ipaddress: IPvAnyAddress, user: dict = Depends(check_role(["admin"]))):
    """
    Delete a reserved IP address from a specified cluster.

    This endpoint removes the specified IP address from the reserved IPs 
    of the given cluster. If the IP address does not exist in the 
    reserved list, a 404 error is returned.

    Args:
        cluster (ClusterNames): The name of the cluster from which the 
        IP address is to be removed. Should match one of the defined 
        cluster names.
        
        ipaddress (IPvAnyAddress): The IP address to be removed. 
        Must be a valid IPv4 or IPv6 address.

    Raises:
        HTTPException: If the IP address is not found in the reserved 
        IPs of the specified cluster, a 404 error is raised with 
        details about the failure.

    Returns:
        Dict[str, str]: A dictionary containing the removed IP address 
        along with the associated cluster name.

    Example:
        DELETE /ip/my_cluster/192.168.1.10
        Response:
        {
            "msg": "192.168.1.10 has been removed from cluster my_cluster",
            "cluster": "my_cluster"
        }

        DELETE /ip/my_cluster/192.168.1.99
        Response:
        {
            "msg": "Address not found",
            "cluster": "my_cluster",
            "ip": "192.168.1.99"
        }
    """
    db_cluster = db[cluster.name]
    reserved_ips = db_cluster["reserved_ips"]
    try:
        res = reserved_ips.pop(str(ipaddress))
    except KeyError:
        raise HTTPException(status_code=404, detail={"msg": "Address not found", "cluster": cluster.name, "ip": str(ipaddress)})
    return res | {'cluster': cluster}

@app.get("/ip/{cluster}")
async def get_ip(cluster: ClusterNames, user: dict = Depends(check_role(["user"]))):
    """
    Reserve an IP address from a pool for a given cluster.

    The reserved IP address and its expiration time are returned in the response.

    Args:
        cluster (ClusterNames): The name of the cluster from which to reserve an IP.

    Returns:
        dict: A dictionary containing the reserved IP address, its prefix length,
        its expiration time, and the associated cluster name.

    Raises:
        HTTPException: If no available IP address can be reserved from the pool, 
        a 404 error is raised.
    """
    cluster_name = cluster.name

    try:
        res = get_ip_in_cluster(cluster_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))    

    return res

def get_ip_in_cluster(cluster_name):
    db_cluster = db[cluster_name]
    reserved_ips = db_cluster["reserved_ips"]

    pool = iplib.generate_ip_pool(db_cluster['prefix'])
    prefix = IPv4Network(db_cluster['prefix'])

    for ip, infos in reserved_ips.items():
        pool.discard(infos["ip"])

    reserved_ip = iplib.pick_and_remove_ip(pool)
    
    entry= {
        "ip": reserved_ip,
        "prefixlen": prefix.prefixlen,
        "expiration": expiration_time()
        }
    db_cluster['reserved_ips'][str(reserved_ip)] = entry
    
    return entry | {"cluster": cluster_name}

@app.get("/db/")
async def get_db(user: dict = Depends(check_role(["admin", "user"]))):
    return {"db": db}

@app.get("/reset/")
async def get_reset(user: dict = Depends(check_role(["admin"]))):
    global db
    db = load_db()
    return {"db": db}

@app.post("/pos/script/")
async def post_pos_script(data: pos.PosScriptData, user: dict = Depends(check_role(["user"]))):
    # deploy_node = data.deploy_node
    # url = data.xp_url

    # generate the inventory
    inventory = pos.generate_inventory(data=data)

    # generate the Ansible playbook
    playbook = pos.generate_playbook()

    # generate the Ansible playbook
    playbook_5g = pos.generate_playbook_5g()

    # generate the exectution script
    deploy = pos.generate_script(data=data)

    # generate dmi parameters
    dmi = pos.generate_dmi(data=data, user=user)

    # Create a Zip file with all content
    zip_buffer = BytesIO()
    # Add content to the zip file
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        zip_file.writestr("pos/deploy.sh", deploy)
        zip_file.writestr("pos/provision.yaml", playbook)
        zip_file.writestr("pos/5g.yaml", playbook_5g)
        zip_file.writestr("pos/params_dmi.yaml", dmi)
        zip_file.writestr("pos/hosts", inventory)

    oai = pos.generate_oai(data=data, gip=get_ip_in_cluster, zip_buffer=zip_buffer)
    
    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer, 
        media_type="application/x-zip-compressed", 
        headers={"Content-Disposition": "attachment; filename=pos.zip"}
    )



#     file_like = StringIO(pos.generate_script(deploy_node=deploy_node))
#     return StreamingResponse(file_like, media_type="text/plain", headers={"Content-Disposition": "attachment; filename=deploy.sh"})
#     # return Response(content=pos.generate_script(deploy_node=deploy_node), media_type="text/plain")

# @app.post("/pos/inventory/{deploy_node}")
# async def post_pos_inventory(deploy_node: str, user: dict = Depends(check_role(["user"]))):
#     file_like = StringIO(pos.generate_inventory(deploy_node=deploy_node))
#     return StreamingResponse(file_like, media_type="text/yaml", headers={"Content-Disposition": "attachment; filename=hosts"})
#     # return Response(content=pos.generate_inventory(deploy_node=deploy_node), media_type="text/plain")