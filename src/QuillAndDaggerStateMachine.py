import logging
import time
from datetime import datetime

from QADState import QADState


PREPARATION_STAGE = QADState("PREPARATION_STAGE")
WRITING_STAGE = QADState("WRITING_STAGE")
REVIEW_STAGE = QADState("REVIEW_STAGE")
RESULT_STAGE = QADState("RESULT_STAGE")

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
                 review_phase_time_in_days, timezone):
        self.logger = logging.getLogger("QuillAndDagger")
        self.prompt_manager = prompt_manager
        self.timezone = timezone
        self.time_map = {
            PREPARATION_STAGE: datetime.fromisoformat(preparation_phase_time_in_days).astimezone(timezone),
            WRITING_STAGE: datetime.fromisoformat(writing_phase_time_in_days).astimezone(timezone),
            REVIEW_STAGE: datetime.fromisoformat(review_phase_time_in_days).astimezone(timezone)
        }

    def switch_state(self):
        if self.current_state in state_map:
            self.logger.info(f"Transitioning from state {self.current_state} to state {state_map[self.current_state]}")
            self.current_state = state_map[self.current_state]
            self.schedule_state_switch()

    def schedule_state_switch(self):
        if self.current_state != RESULT_STAGE:
            self.logger.info(f"Scheduling next state switch to {self.time_map[self.current_state]}")
            if self.current_state == WRITING_STAGE:
                self.prompt_manager.decide_prompt()
            self.start_timed_stage_switch(self.time_map[self.current_state])

    def get_current_state(self):
        return self.current_state

    def get_current_time_target(self):
        return self.current_time_target

    def start_timed_stage_switch(self, target_time):
        self.current_time_target = target_time
        last_time = datetime.now(self.timezone).replace(microsecond=0)
        should_run = True
        while should_run:
            distance = target_time - last_time
            # distance.seconds is capped at 86400 which means it will sleep at most one day
            # if the scheduled state switch is on the same day, it will be scheduled
            time.sleep(distance.seconds)
            last_time = datetime.now(self.timezone).replace(microsecond=0)
            self.logger.info(f"Checking for possible state switch..")
            if target_time < last_time:
                should_run = False
                self.switch_state()
