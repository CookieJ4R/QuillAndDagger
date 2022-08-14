import logging
import os
from random import Random

from SingleValueJSONDB import SingleValueJSONDB


class PromptManager:
    active_prompt = None

    def __init__(self):
        self.logger = logging.getLogger("QuillAndDagger")
        self.prompt_db = SingleValueJSONDB("prompts")
        self.load_active_prompt()

    def load_active_prompt(self):
        if os.path.exists("data/active_prompt"):
            self.logger.info(f"Prompt has already been chosen. Loading...")
            with open("data/active_prompt", "r") as file:
                self.active_prompt = file.readline().strip()
                self.logger.info(f"Set active prompt to {self.active_prompt}")
                file.close()
        else:
            self.active_prompt = None
            self.logger.info(f"Set active prompt to {self.active_prompt}")

    def decide_prompt(self):
        self.logger.info("Deciding prompt...")
        if self.active_prompt is None:
            rnd = Random()
            self.active_prompt = self.prompt_db.get(rnd.randint(0, self.prompt_db.get_size() - 1))
            self.logger.info(f"Decided on prompt {self.active_prompt}")
            with open("data/active_prompt", "w") as file:
                file.write(self.active_prompt)
                self.logger.info("Saved chosen prompt to data/active_prompt")
                file.close()
        return self.active_prompt

    def is_prompt_active(self):
        return self.active_prompt is not None
