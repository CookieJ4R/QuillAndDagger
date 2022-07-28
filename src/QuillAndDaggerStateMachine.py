import time
from datetime import datetime

import pytz

from QADState import QADState

PREPARATION_STAGE = QADState()
WRITING_STAGE = QADState()
REVIEW_STAGE = QADState()
RESULT_STAGE = QADState()

state_map = {
    PREPARATION_STAGE: WRITING_STAGE,
    WRITING_STAGE: REVIEW_STAGE,
    REVIEW_STAGE: RESULT_STAGE
}


class QuillAndDaggerStateMachine:
    current_state: QADState = PREPARATION_STAGE
    current_time_target = None

    def __init__(self, prompt_manager, preparation_phase_time_in_days,
                 writing_phase_time_in_days,
                 review_phase_time_in_days):
        self.prompt_manager = prompt_manager
        self.preparation_stage_time_in_days = preparation_phase_time_in_days
        self.writing_stage_time_in_days = writing_phase_time_in_days
        self.review_stage_time_in_days = review_phase_time_in_days

    # TODO change time calculation so 14 days really mean 14 days instead of based on current time
    def switch_state(self):
        if self.current_state in state_map:
            print("Transitioning state")
            self.current_state = state_map[self.current_state]
            self.schedule_state_switch()

    def schedule_state_switch(self):
        date = datetime.now(pytz.timezone("Europe/Berlin"))
        # TODO day month year wrapping
        if self.current_state == PREPARATION_STAGE:
            self.start_timed_stage_switch(date.replace(microsecond=0, second=0, minute=0, hour=0,
                                                       day=date.day + self.preparation_stage_time_in_days))
        elif self.current_state == WRITING_STAGE:
            self.prompt_manager.decide_prompt()
            self.start_timed_stage_switch(date.replace(microsecond=0, second=0, minute=0, hour=0,
                                                       day=date.day + self.writing_stage_time_in_days))
        elif self.current_state == REVIEW_STAGE:
            self.start_timed_stage_switch(date.replace(microsecond=0, second=0, minute=0, hour=0,
                                                       day=date.day + self.review_stage_time_in_days))

    def get_current_state(self):
        return self.current_state

    def get_current_time_target(self):
        return self.current_time_target

    def start_timed_stage_switch(self, target_time):
        # TODO time calculation needs to be updated - currently its not clear if
        # it triggers only a tfull minute or once countdown is reached
        self.current_time_target = target_time
        last_time = datetime.now(pytz.timezone("Europe/Berlin"))
        should_run = True
        while should_run:
            time.sleep(60 - last_time.second)

            last_time = datetime.now(pytz.timezone("Europe/Berlin"))
            if target_time < last_time:
                should_run = False
                self.switch_state()
