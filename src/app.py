import logging
import os
import sys
import time
from datetime import datetime
from os.path import basename
from threading import Thread
from zipfile import ZipFile

import configparser
import pytz
from flask import Flask, session, send_from_directory, request, redirect, render_template, send_file
from waitress import serve
from werkzeug.utils import secure_filename

from AliasGenerator import AliasGenerator
from JSONDB import JSONDB
from PromptManager import PromptManager
from QuillAndDaggerStateMachine import QuillAndDaggerStateMachine, PREPARATION_STAGE, WRITING_STAGE, REVIEW_STAGE, \
    RESULT_STAGE
from SingleValueJSONDB import SingleValueJSONDB
from util import is_authenticated_session, get_list_of_submission_names_for, build_results

app = Flask(__name__, template_folder='../templates')
app.secret_key = "ijwo0hDFj2JKD7sf09hfoinin2"

logger = logging.getLogger("QuillAndDagger")


@app.route("/preparation_phase")
def build_preparation_stage_page():
    if not is_authenticated_session(session):
        return redirect("/authenticate")
    if state_machine.get_current_state() != PREPARATION_STAGE:
        return redirect("/")
    return render_template("preparation_stage.html", alias=session['alias'],
                           target_date=state_machine.get_current_time_target())


@app.route("/writing_phase", methods=['GET', 'POST'])
def build_writing_stage_page():
    if not is_authenticated_session(session):
        return redirect("/authenticate")
    if state_machine.get_current_state() != WRITING_STAGE:
        return redirect("/")
    if request.method == 'POST':
        if request.form.get('submit_story') is not None:
            if state_machine.get_current_state() != WRITING_STAGE:
                return "Writing phase is already finished. Your submission as rejected - Please reload the page!"
            f = request.files['submission']
            f.save(os.path.join(config["APP"]["submission_folder"], secure_filename(session["alias"] + ".pdf")))
    return render_template("writing_phase.html", alias=session['alias'], prompt=prompt_manager.active_prompt,
                           target_date=state_machine.get_current_time_target())


@app.route("/review_phase", methods=['GET', 'POST'])
def build_review_stage_page():
    if not is_authenticated_session(session):
        return redirect("/authenticate")
    elif state_machine.get_current_state() != REVIEW_STAGE:
        return redirect("/")
    elif review_completion_db.has_value(session['alias']):
        return render_template("review_phase_completed.html", alias=session['alias'],
                               target_date=state_machine.get_current_time_target())
    if request.method == 'POST':
        for review in request.form:
            review_db.put(review.split("_")[1], [int(request.form.get(review))])
        review_completion_db.put(session['alias'])
        return render_template("review_phase_completed.html", alias=session['alias'],
                               target_date=state_machine.get_current_time_target())
    list_of_submissions_to_review = get_list_of_submission_names_for(config["APP"]["submission_folder"], session)
    return render_template("review_phase.html", alias=session['alias'],
                           target_date=state_machine.get_current_time_target(),
                           submission_list=list_of_submissions_to_review)


@app.route("/result_phase")
def build_result_stage_page():
    if not is_authenticated_session(session):
        return redirect("/authenticate")
    if state_machine.get_current_state() != RESULT_STAGE:
        return redirect("/")
    results = build_results(review_db)
    return render_template("result_phase.html", alias=session['alias'], results=results)


def build_authentication_page():
    return render_template("authentication.html")


@app.route('/download_files')
def download_files():
    if not is_authenticated_session(session):
        return redirect("/authenticate")
    if state_machine.get_current_state() != REVIEW_STAGE:
        return redirect("/")
    with ZipFile(config["APP"]["submission_folder"] + '/SubmissionsFor' + session['alias'] + '.zip', 'w') \
            as zipObj:
        for file in os.listdir(config["APP"]["submission_folder"]):
            if file.endswith(".pdf") and not file.startswith(session['alias']):
                file_path = os.path.join(config["APP"]["submission_folder"], file)
                zipObj.write(file_path, basename(file_path))
    return send_file("../" + os.path.join(config["APP"]["submission_folder"], 'SubmissionsFor' + session['alias'] +
                                          '.zip'), download_name='submissions.zip', as_attachment=True)


@app.route('/')
def index():
    if not is_authenticated_session(session):
        return redirect("/authenticate")
    if state_machine.get_current_state() == PREPARATION_STAGE:
        return redirect("/preparation_phase")
    elif state_machine.get_current_state() == WRITING_STAGE:
        return redirect("/writing_phase")
    elif state_machine.get_current_state() == REVIEW_STAGE:
        return redirect("/review_phase")
    elif state_machine.get_current_state() == RESULT_STAGE:
        return redirect("/result_phase")


@app.route('/authenticate', methods=['GET', 'POST'])
def authenticate():
    if is_authenticated_session(session):
        return redirect("/")
    logger.info("incoming request")
    if request.method == 'POST':
        logger.info(f"received post")
        logger.info(f"received auth")
        if "uid" in request.form:
            uuid = request.form.get("uid").strip()
            logger.info(f"received {uuid}")
            if uuid_db.has_value(uuid):
                if alias_db.does_key_exist(uuid):
                    alias = alias_db.get(uuid)
                    logger.info(f"Authenticated! {alias} logged in!")
                    session['alias'] = alias
                else:
                    logger.info("User without alias tries to authenticate. Generating new alias...")
                    alias = alias_generator.generate_alias(alias_db.database.values())
                    alias_db.put(uuid, alias)
                    session['alias'] = alias
                return redirect("/")
            else:
                logger.warning("Someone tried to authenticate with an unknown UUID")
    return build_authentication_page()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    prompt_manager = PromptManager()
    config = configparser.ConfigParser()
    config.read("data/app_config.ini")
    state_machine = QuillAndDaggerStateMachine(prompt_manager,
                                               config["STATE_MACHINE"]["preparation_phase_end"],
                                               config["STATE_MACHINE"]["writing_phase_end"],
                                               config["STATE_MACHINE"]["review_phase_end"],
                                               pytz.timezone(config["STATE_MACHINE"]["timezone"]))

    initial_state = int(config["STATE_MACHINE"]["initial_state"])
    if initial_state == 0:
        state_machine.current_state = PREPARATION_STAGE
    elif initial_state == 1:
        if not prompt_manager.is_prompt_active():
            prompt_manager.decide_prompt()
        state_machine.current_state = WRITING_STAGE
    elif initial_state == 2:
        state_machine.current_state = REVIEW_STAGE
    elif initial_state == 3:
        state_machine.current_state = RESULT_STAGE

    uuid_db = SingleValueJSONDB("uuid_db")
    alias_db = JSONDB("alias_db")
    review_db = JSONDB("review_db")
    review_completion_db = SingleValueJSONDB("review_completion_db")
    server_thread = Thread(target=serve, args=[app], kwargs={'host': config["WEBSERVER"]["ip"],
                                                             'port': int(config["WEBSERVER"]["port"])}, daemon=True)
    server_thread.start()
    alias_generator = AliasGenerator()
    date = datetime.now(pytz.timezone(config["STATE_MACHINE"]["timezone"]))
    state_machine.schedule_state_switch()
    while True:
        try:
            logger.info("Server is in result phase. Can be exited anytime with Ctrl+C. This message repeats every 5 "
                        "minutes.")
            time.sleep(60 * 5)
        except KeyboardInterrupt:
            logger.info("Shutting down QuillAndDagger!")
            sys.exit()
