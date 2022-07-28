import os
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

DEFAULT_PREPARATION_STAGE_TIME_IN_DAYS = 7
DEFAULT_WRITING_STAGE_TIME_IN_DAYS = 14
DEFAULT_REVIEW_STAGE_TIME_IN_DAYS = 7

app = Flask(__name__, template_folder='../templates')
app.secret_key = "ijwo0hDFj2JKD7sf09hfoinin2"
app.config['STATIC_FOLDER'] = "../static_without_route"
app.config['SUBMISSIONS_FOLDER'] = "../submissions"


# TODO add better logging
# TODO unify configparser usage


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
            f.save(os.path.join(app.config['SUBMISSIONS_FOLDER'], secure_filename(session["alias"] + ".pdf")))
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
    list_of_submissions_to_review = get_list_of_submission_names_for(app.config['SUBMISSIONS_FOLDER'], session)
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
    return send_from_directory(app.config['STATIC_FOLDER'], "authentication.html")


@app.route('/download_files')
def download_files():
    if not is_authenticated_session(session):
        return redirect("/authenticate")
    if state_machine.get_current_state() != REVIEW_STAGE:
        return redirect("/")
    with ZipFile(app.config['SUBMISSIONS_FOLDER'] + '/SubmissionsFor' + session['alias'] + '.zip', 'w') \
            as zipObj:
        for file in os.listdir(app.config['SUBMISSIONS_FOLDER']):
            if file.endswith(".pdf") and not file.startswith(session['alias']):
                file_path = os.path.join(app.config['SUBMISSIONS_FOLDER'], file)
                zipObj.write(file_path, basename(file_path))
    return send_file(os.path.join(app.config['SUBMISSIONS_FOLDER'], 'SubmissionsFor' + session['alias'] + '.zip'),
                     download_name='submissions.zip', as_attachment=True)


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
    if request.method == 'POST':
        if request.form.get('Authenticate') == 'Authenticate':
            uuid = request.form.get("uid").strip()
            print(uuid)
            if uuid_db.has_value(uuid):
                if alias_db.does_key_exist(uuid):
                    session['alias'] = alias_db.get(uuid)
                else:
                    print("generating alias")
                    alias = alias_generator.generate_alias(alias_db.database.values())
                    alias_db.put(uuid, alias)
                    session['alias'] = alias
                return redirect("/")
    return build_authentication_page()


if __name__ == '__main__':
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
    server_thread = Thread(target=serve, args=[app], kwargs={'host': config["APP"]["ip"],
                                                             'port': int(config["APP"]["port"])}, daemon=True)
    server_thread.start()
    alias_generator = AliasGenerator()
    date = datetime.now(pytz.timezone(config["STATE_MACHINE"]["timezone"]))
    state_machine.schedule_state_switch()
    while True:
        print("Server is in result phase. Can be exited anytime with Ctrl+C. This message repeats every 5 minutes.")
        time.sleep(60*5)
