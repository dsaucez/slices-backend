from enum import Enum
from fastapi import FastAPI, HTTPException, Depends, Security, status
from fastapi.security import APIKeyHeader
from pydantic import IPvAnyAddress
from datetime import datetime, timedelta, timezone
import ip as iplib
from ipaddr import IPAddress, IPv4Network
import json

# == API KEY ===================================================================
import jwt
api_key_header = APIKeyHeader(name="Bearer")

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
async def delete_ip(cluster: ClusterNames, ipaddress: IPvAnyAddress):
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
async def get_ip(cluster: ClusterNames):
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
    db_cluster = db[cluster.name]
    reserved_ips = db_cluster["reserved_ips"]

    pool = iplib.generate_ip_pool(db_cluster['prefix'])
    prefix = IPv4Network(db_cluster['prefix'])

    for ip, infos in reserved_ips.items():
        pool.discard(infos["ip"])

    try:
        reserved_ip = iplib.pick_and_remove_ip(pool)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    entry= {
        "ip": reserved_ip,
        "prefixlen": prefix.prefixlen,
        "expiration": expiration_time()
        }
    db_cluster['reserved_ips'][str(reserved_ip)] = entry
    
    return entry | {"cluster": cluster}

@app.get("/db/")
async def get_db():
    return {"db": db}