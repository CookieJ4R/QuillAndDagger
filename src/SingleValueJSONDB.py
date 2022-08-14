import json
import logging
import os

DATA_STORAGE_PATH = "data/"


class SingleValueJSONDB:
    database = None
    db_path = None

    def __init__(self, filename):
        self.logger = logging.getLogger("QuillAndDagger")
        self.db_path = DATA_STORAGE_PATH + filename
        if os.path.exists(self.db_path):
            self.logger.info(f"Database {self.db_path} exists.. opening")
            self.database = self.load_database()
        else:
            self.logger.info(f"Database {self.db_path} does not exist.. creating empty database")
            self.database = []

    def load_database(self):
        with open(self.db_path, "r") as file:
            self.logger.info(f"Loading database from {self.db_path}")
            return json.load(file)

    def save_database(self):
        with open(self.db_path, "w") as file:
            self.logger.info(f"Saving database to {self.db_path}")
            file.write(json.dumps(self.database))
            file.close()

    def put(self, value):
        self.logger.info(f"Adding {value} to database {self.db_path}")
        self.database.append(value)
        self.save_database()

    def get(self, index):
        self.logger.info(f"Getting value from index {index} from database {self.db_path}")
        return self.database[index]

    def has_value(self, value):
        return value in self.database

    def get_size(self):
        return len(self.database)
