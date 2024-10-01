import ipaddress
import random

def generate_ip_pool(prefix):
  """
  Generate a pool of usable IP addresses from a given IPv4 network prefix.

  This function takes a network prefix in CIDR notation (e.g., '192.0.2.0/24')
  and returns a set of all usable host IP addresses within that network.

  Args:
      prefix (str): A string representing the network prefix in CIDR notation.

  Returns:
      set: A set of IPv4 addresses (as IPv4Address objects) that are usable 
            within the specified network, excluding network and broadcast addresses.
  """
  network = ipaddress.IPv4Network(prefix)
  ip_pool = set(network.hosts())

  return ip_pool

def pick_and_remove_ip(ip_pool):
  """
  Select and remove a random IP address from a given IP pool.

  This function picks a random IP address from the provided set of IP addresses
  and removes it from the pool. If the pool is empty, it raises a ValueError.

  Args:
      ip_pool (set): A set of IP addresses (as IPv4Address objects) from which to 
                      pick and remove an IP address.

  Returns:
      IPv4Address: The randomly selected IP address that has been removed from the pool.

  Raises:
      ValueError: If the ip_pool is empty.
  """
  if not ip_pool:
    raise ValueError("The IP pool is empty!")
  
  selected_ip = random.choice(list(ip_pool))
  ip_pool.remove(selected_ip)

  return selected_ip