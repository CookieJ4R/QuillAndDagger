import json
import os

DATA_STORAGE_PATH = "data/"


class JSONDB:
    database = None
    db_path = None

    def __init__(self, filename):
        self.db_path = DATA_STORAGE_PATH + filename
        if os.path.exists(self.db_path):
            self.database = self.load_database()
        else:
            self.database = {}

    def load_database(self):
        with open(self.db_path, "r") as file:
            return json.load(file)

    def save_database(self):
        with open(self.db_path, "w") as file:
            file.write(json.dumps(self.database))
            file.close()

    def put(self, key, value):
        if isinstance(value, list):
            if key in self.database:
                self.database[key] += value
                self.save_database()
                return
        self.database[key] = value
        self.save_database()

    def get(self, key):
        return self.database[key]

    def does_value_exist(self, value):
        return value in self.database.values()

    def does_key_exist(self, key):
        print(key)
        print(self.database)
        print(key in self.database)
        return key in self.database
