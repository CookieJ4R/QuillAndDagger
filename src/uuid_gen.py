import uuid

import argparse as argparse

from SingleValueJSONDB import SingleValueJSONDB

uuid_db = SingleValueJSONDB("uuid_db")


parser = argparse.ArgumentParser()
parser.add_argument("count", type=int)
parser.add_argument("--dont_add_to_db", action=argparse.BooleanOptionalAction)

args = parser.parse_args()

for i in range(args.count):
    u_id = str(uuid.uuid4())

    print("Generated: %s" % u_id)
    if not args.dont_add_to_db:
        uuid_db.put(u_id)
