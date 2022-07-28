from random import Random


class AliasGenerator:

    def __init__(self):
        self.praefix_list = self.load_praefix_list()
        self.suffix_list = self.load_suffix_list()
        self.rnd = Random()

    @staticmethod
    def load_praefix_list():
        with open("data/praefix_list", "r") as file:
            return list(map(lambda line: line.strip(), file.readlines()))

    @staticmethod
    def load_suffix_list():
        with open("data/suffix_list", "r") as file:
            return list(map(lambda line: line.strip(), file.readlines()))

    def generate_alias(self, existing_aliases) -> str:
        alias = None
        while alias is None and alias not in existing_aliases:
            praefix = self.praefix_list[self.rnd.randrange(0, len(self.praefix_list) - 1)]
            print("chosen praefix %s" % praefix)
            suffix = self.suffix_list[self.rnd.randrange(0, len(self.suffix_list) - 1)]
            print("chosen suffix %s" % suffix)
            alias = praefix + suffix
            print("generated alias %s" % alias)
        return alias
