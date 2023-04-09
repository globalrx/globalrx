import json
import os
import sys

import psycopg


def main():
    DATABASE_URL = os.environ.get("DATABASE_URL")
    try:
        print('trying to connect')
        psycopg.connect(
            DATABASE_URL
        )
        print('connected')
    except psycopg.OperationalError:
        print('exiting?')
        sys.exit(-1)
    sys.exit(0)

if __name__ == '__main__':
    main()
