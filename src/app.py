import logging
import os
import sys
import time
from datetime import datetime
from os.path import basename
from threading import Thread
from zipfile import ZipFile
import requests
import configparser
import pytz
from flask import Flask, session, request, redirect, render_template, send_file
from waitress import serve
from werkzeug.utils import secure_filename

from AliasGenerator import AliasGenerator
from JSONDB import JSONDB
from PromptManager import PromptManager
from QuillAndDaggerStateMachine import QuillAndDaggerStateMachine, PREPARATION_STAGE, WRITING_STAGE, REVIEW_STAGE, \
    RESULT_STAGE
from SingleValueJSONDB import SingleValueJSONDB
from util import allowed_file, is_authenticated_session, get_list_of_submission_names_for, build_results

app = Flask(__name__, template_folder='../templates', static_folder='../static')
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
            if not allowed_file(f.filename):
                return render_template("writing_phase.html", alias=session['alias'], prompt=prompt_manager.active_prompt, 
                target_date=state_machine.get_current_time_target(), notification_id=2)
            if not os.path.exists(config["APP"]["submission_folder"]):
                os.mkdir(config["APP"]["submission_folder"])
            f.save(os.path.join(config["APP"]["submission_folder"], secure_filename(session["alias"] + ".pdf")))
    if os.path.exists(os.path.join(config["APP"]["submission_folder"], secure_filename(session["alias"] + ".pdf"))):
        return render_template("writing_phase.html", alias=session['alias'], prompt=prompt_manager.active_prompt,
                           target_date=state_machine.get_current_time_target(), notification_id=1)
    return render_template("writing_phase.html", alias=session['alias'], prompt=prompt_manager.active_prompt,
                           target_date=state_machine.get_current_time_target(), notification_id=0)


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
    results = build_results(review_db, alias_db)
    return render_template("result_phase.html", alias=session['alias'], results=results)


def build_authentication_page(error_msg):
    return render_template("authentication.html", error=error_msg)


@app.route('/download_files')
def download_files():
    if not is_authenticated_session(session):
        return redirect("/authenticate")
    if state_machine.get_current_state() != REVIEW_STAGE:
        return redirect("/")
    if not os.path.exists(config["APP"]["submission_folder"]):
        return "No submissions found!"
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


@app.route('/authenticate')
def authenticate():
    if is_authenticated_session(session):
        return redirect("/")
    if request.method == 'GET':
        if "GUARDTOKEN" in request.args:
            token = request.args["GUARDTOKEN"]
            response = requests.get("https://guard.example.com/sso?GUARDTOKEN=" + token)
            if response.status_code == 200:
                username = response.json()["username"]
                if alias_db.does_key_exist(username):
                    alias = alias_db.get(username)
                    logger.info(f"Authenticated! {alias} logged in!")
                    session['alias'] = alias
                else:
                    if not (state_machine.get_current_state() == PREPARATION_STAGE or
                            state_machine.get_current_state() == WRITING_STAGE):
                        logger.info(f"{username} tried to join a running competition!")
                        auth_error_msg = "Sorry you cant join now. The competition has already begun!"
                        return build_authentication_page(error_msg=auth_error_msg)

                    logger.info("User without alias tries to authenticate. Generating new alias...")
                    alias = alias_generator.generate_alias(alias_db.database.values())
                    alias_db.put(username, alias)
                    session['alias'] = alias
                return redirect("/")
            else:
                logger.warning("Error while authenticating with GUARD")

    return build_authentication_page(error_msg="")


def _setup_logger():
    formatter = logging.Formatter('[%(asctime)s.%(msecs)d]%(name)s|%(levelname)s|%(message)s', datefmt='%H:%M:%S')
    logger.setLevel(logging.DEBUG)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.setFormatter(formatter)

    file_handler = logging.FileHandler('q&d.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stdout_handler)

    logger.info("Logger setup complete")


if __name__ == '__main__':
    _setup_logger()
    authentication_error_msg = ""
    config = configparser.ConfigParser()
    config.read("data/app_config.ini")
    prompt_manager = PromptManager()
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

    alias_db = JSONDB("alias_db")
    review_db = JSONDB("review_db")
    review_completion_db = SingleValueJSONDB("review_completion_db")
    server_thread = Thread(target=serve, args=[app], kwargs={'host': config["WEBSERVER"]["ip"],
                                                             'port': int(config["WEBSERVER"]["port"]),
                                                             '_quiet': True}, daemon=True)
    server_thread.start()
    alias_generator = AliasGenerator()
    state_machine.schedule_state_switch()
    while True:
        try:
            logger.info("Server is in result phase. Can be exited anytime with Ctrl+C. This message repeats every 5 "
                        "minutes.")
            time.sleep(60 * 5)
        except KeyboardInterrupt:
            logger.info("Shutting down QuillAndDagger!")
            sys.exit()
