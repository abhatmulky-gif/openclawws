"""
ASTRA FWA Setup Script
Initialises the TypeDB knowledge graph and verifies Redis connectivity.
Neo4j has been removed entirely — TypeDB is the sole graph backend.

Run this once before starting the ASTRA engine or backend:
  python setup_topology.py
"""

import os
import sys
import redis
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), 'svaya-poc.env')
load_dotenv(env_path)

REDIS_URL = os.getenv('REDIS_URL')

# Import TypeDB setup from the project root
_ROOT = os.path.join(os.path.dirname(__file__), "../..")
sys.path.insert(0, _ROOT)

from topology_typedb import setup_typedb, TYPEDB_HOST, DB_NAME
from fwa_typedb_client import ping as typedb_ping


def test_redis():
    print("Testing Redis connection...")
    if not REDIS_URL:
        print("  [SKIP] REDIS_URL not set in svaya-poc.env")
        return
    try:
        r = redis.from_url(REDIS_URL)
        r.ping()
        print("  Redis: connected")
    except Exception as e:
        print(f"  Redis: connection failed — {e}")


def setup_all(recreate: bool = True):
    print("=" * 55)
    print("ASTRA FWA Setup")
    print(f"Graph Backend: TypeDB @ {TYPEDB_HOST}  (db: {DB_NAME})")
    print("=" * 55)
    print()

    # 1. Redis
    test_redis()
    print()

    # 2. TypeDB — schema + pilot data
    try:
        setup_typedb(recreate=recreate)
    except Exception as e:
        print(f"\nTypeDB setup failed: {e}")
        print(f"Make sure TypeDB Core is running on {TYPEDB_HOST}")
        sys.exit(1)

    # 3. Verify client can connect
    print()
    if typedb_ping():
        print(f"TypeDB client ping: OK  (database '{DB_NAME}' ready)")
    else:
        print(f"TypeDB client ping: FAILED  (database '{DB_NAME}' not found after setup)")

    print("\nSetup complete. Start the ASTRA backend with:")
    print("  python backend.py")
    print("Start the ASTRA engine with:")
    print("  python skills/svaya-noc/svaya_engine.py")


if __name__ == "__main__":
    recreate = "--no-recreate" not in sys.argv
    setup_all(recreate=recreate)
