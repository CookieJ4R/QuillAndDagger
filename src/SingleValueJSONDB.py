import json
import os

DATA_STORAGE_PATH = "data/"


class SingleValueJSONDB:
    database = None
    db_path = None

    def __init__(self, filename):
        self.db_path = DATA_STORAGE_PATH + filename
        if os.path.exists(self.db_path):
            self.database = self.load_database()
        else:
            self.database = []

    def load_database(self):
        with open(self.db_path, "r") as file:
            return json.load(file)

    def save_database(self):
        with open(self.db_path, "w") as file:
            file.write(json.dumps(self.database))
            file.close()

    def put(self, value):
        self.database.append(value)
        self.save_database()

    def get(self, index):
        return self.database[index]

    def has_value(self, value):
        return value in self.database

    def get_size(self):
        return len(self.database)
