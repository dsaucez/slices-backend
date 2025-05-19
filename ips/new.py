import sqlite3
import logging
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def create_allocations_table(conn):
    """Create the 'allocation' table in the SQLite database with automatic timestamp."""
    cursor = conn.cursor()

    # Enable foreign key support
    cursor.execute("PRAGMA foreign_keys = ON")

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS allocations (
        ip TEXT NOT NULL UNIQUE,
        prefix TEXT NOT NULL UNIQUE,
        owner TEXT NOT NULL,
        allocation_time TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
        expiration_time TEXT NOT NULL,
        experiment_id TEXT NOT NULL UNIQUE,
        FOREIGN KEY (ip) REFERENCES ips(ip_address),
        FOREIGN KEY (prefix) REFERENCES subnets(subnet)
    )
    ''')

    logger.debug("Allocation table created successfully with automatic timestamp.")

def create_subnets_table(conn):  
  # Create table for subnets with subnet as primary key
  cursor = conn.cursor()

  cursor.execute('''
  CREATE TABLE IF NOT EXISTS subnets (
      subnet TEXT PRIMARY KEY
  )
  ''')

def create_ips_table(conn):
  cursor = conn.cursor()

  # Create table for IP addresses with ip_address as primary key
  cursor.execute('''
  CREATE TABLE IF NOT EXISTS ips (
      ip_address TEXT PRIMARY KEY
  )
  ''')

def create_db(db_path='network_data.db'):
  # Create/connect to SQLite database
  conn = sqlite3.connect(db_path)

  create_subnets_table(conn)
  create_ips_table(conn)
  create_allocations_table(conn)

  # Commit and close connection
  conn.commit()
  conn.close()

  logger.debug("Database and tables created successfully.")


class AllocationError(Exception):
    """Base exception for allocation-related errors."""
    pass

class NoIPAvailable(AllocationError):
    """Raised when no unallocated IP addresses are available."""
    def __init__(self, message="No available IP addresses for allocation."):
        super().__init__(message)

class NoPrefixAvailable(AllocationError):
    """Raised when no unallocated subnets (prefixes) are available."""
    def __init__(self, message="No available subnets (prefixes) for allocation."):
        super().__init__(message)


def load_json_file(file_path):
    """Load and return the contents of a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        print(f"Invalid JSON format: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")


def get_allocation(owner, experiment_id, duration=120, db_path='network_data.db'):
    """Return the allocation details for a given experiment_id."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT ip, prefix
            FROM allocations
            WHERE experiment_id = ?
        ''', (experiment_id,))

        allocation = cursor.fetchone()

        if allocation:
            ip, prefix = allocation
        else:
            ip, prefix = allocate_ip_to_subnet(owner=owner, experiment_id=experiment_id, duration=duration, db_path='network_data.db')

        return {"ip": ip, "prefix": prefix}
    except sqlite3.Error as e:
        logger.error(f"Error retrieving allocation for experiment_id '{experiment_id}': {e}")
    finally:
        conn.close()

def allocate_ip_to_subnet(owner, experiment_id, duration=120, db_path='network_data.db'):
    """Automatically allocate an IP from the 'ips' table and a subnet from the 'subnets' table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")

    try:
        # Get the first available IP that hasn't been allocated
        cursor.execute('''
            SELECT ip_address FROM ips
            WHERE ip_address NOT IN (SELECT ip FROM allocations)
            LIMIT 1
        ''')
        ip_row = cursor.fetchone()

        if ip_row is None:
            raise NoIPAvailable()

        ip = ip_row[0]

        # Get the first available subnet that hasn't been allocated
        cursor.execute('''
            SELECT subnet FROM subnets
            WHERE subnet NOT IN (SELECT prefix FROM allocations)
            LIMIT 1
        ''')
        prefix_row = cursor.fetchone()

        if prefix_row is None:
            raise NoPrefixAvailable()

        prefix = prefix_row[0]

        allocation_time = datetime.utcnow()
        expiration_time = allocation_time + timedelta(minutes=duration)

        # Format timestamps as string
        allocation_time_str = allocation_time.strftime('%Y-%m-%d %H:%M:%S')
        expiration_time_str = expiration_time.strftime('%Y-%m-%d %H:%M:%S')


        # Now insert the allocation
        cursor.execute('''
            INSERT INTO allocations (ip, prefix, owner, experiment_id, allocation_time, expiration_time)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (ip, prefix, owner, experiment_id, allocation_time_str, expiration_time_str))

        conn.commit()
        logger.debug(f"Allocated IP {ip} to subnet {prefix} for owner '{owner}' in experiment '{experiment_id}'.")

    except sqlite3.IntegrityError as e:
        logger.debug(f"Allocation failed: {e}")
    finally:
        conn.close()

    return (ip, prefix)


def delete_allocation(experiment_id, db_path='network_data.db'):
    """Delete an allocation entry by experiment_id."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Delete the allocation where the experiment_id matches
        cursor.execute('''
            DELETE FROM allocations WHERE experiment_id = ?
        ''', (experiment_id,))

        if cursor.rowcount == 0:
            logger.debug(f"No allocation found with experiment_id '{experiment_id}'.")
        else:
            conn.commit()
            logger.debug(f"Allocation with experiment_id '{experiment_id}' deleted successfully.")

    except sqlite3.Error as e:
        logger.debug(f"Error deleting allocation: {e}")
    finally:
        conn.close()

def remaining_ips(db_path='network_data.db'):
    """Return the number of IPs that have not been allocated."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT COUNT(*) FROM ips
            WHERE ip_address NOT IN (SELECT ip FROM allocations)
        ''')
        remaining_ip_count = cursor.fetchone()[0]
        return remaining_ip_count
    except sqlite3.Error as e:
        logger.debug(f"Error retrieving remaining IPs: {e}")
    finally:
        conn.close()
    

def remaining_subnets(db_path='network_data.db'):
    """Return the number of subnets that have not been allocated."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT COUNT(*) FROM subnets
            WHERE subnet NOT IN (SELECT prefix FROM allocations)
        ''')
        remaining_subnet_count = cursor.fetchone()[0]
        return remaining_subnet_count
    except sqlite3.Error as e:
        logger.debug(f"Error retrieving remaining subnets: {e}")
    finally:
        conn.close()

def remove_expired_allocations(db_path='network_data.db'):
    """
    Remove all allocations whose expiration_time is earlier than the current time.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Delete rows where expiration_time is in the past
        cursor.execute('''
            DELETE FROM allocations
            WHERE expiration_time < CURRENT_TIMESTAMP
        ''')

        conn.commit()
        print(f"Removed {cursor.rowcount} expired allocation(s).")

    except sqlite3.Error as e:
        print(f"Database error while removing expired allocations: {e}")
    finally:
        conn.close()

def add_subnets(subnet_input, db_path='network_data.db'):
    """Add one or more subnets to the 'subnets' table in the SQLite database."""
    # Normalize input to a list
    if isinstance(subnet_input, str):
        subnet_list = [subnet_input]
    elif isinstance(subnet_input, list):
        subnet_list = subnet_input
    else:
        raise ValueError("Input must be a string or a list of strings.")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for subnet in subnet_list:
        try:
            cursor.execute("INSERT INTO subnets (subnet) VALUES (?)", (subnet,))
        except sqlite3.IntegrityError:
            logger.debug(f"Subnet '{subnet}' already exists in the database. Skipping.")

    conn.commit()
    conn.close()
    logger.debug("Subnet(s) added.")

def add_ips(ip_input, db_path='network_data.db'):
    """Add one or more IP addresses to the 'ips' table in the SQLite database."""
    # Normalize input to a list
    if isinstance(ip_input, str):
        ip_list = [ip_input]
    elif isinstance(ip_input, list):
        ip_list = ip_input
    else:
        raise ValueError("Input must be a string or a list of strings.")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for ip in ip_list:
        try:
            cursor.execute("INSERT INTO ips (ip_address) VALUES (?)", (ip,))
        except sqlite3.IntegrityError:
            logger.debug(f"IP '{ip}' already exists in the database. Skipping.")

    conn.commit()
    conn.close()
    logger.debug("IP address(es) added.")


if __name__ == '__main__':
  if not logger.hasHandlers():
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

  create_db(db_path='network_data.db')

  data = load_json_file('pool.json')
  add_ips(data["ips"])
  add_subnets(data["subnets"])

  # remove_old_allocations(duration_minutes=1)
  remove_expired_allocations()
  logger.info(f"remaining IPs: {remaining_ips()}")
  logger.info(f"remaining subnets: {remaining_subnets()}")

  for i in range(100):
    xp = f"xp_{i}"

    a = get_allocation(owner="dsaucezi", experiment_id=xp, duration=1)
    logger.info(f"allocation for {xp} is {a}")

    logger.info(f"remaining IPs: {remaining_ips()}")
    logger.info(f"remaining subnets: {remaining_subnets()}")