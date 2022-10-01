import logging
import os

from JSONDB import JSONDB

logger = logging.getLogger("QuillAndDagger")


def is_authenticated_session(session) -> bool:
    if 'alias' in session:
        return True
    return False


def get_list_of_submission_names_for(path, session) -> list:
    logger.info(f"Getting submission names for {session['alias']}...")
    file_list = []
    if not os.path.exists(path):
        return []
    for file in os.listdir(path):
        if file.endswith(".pdf") and not file.startswith(session['alias']):
            file_list.append(file[0:-4])
    return file_list


def build_results(review_db: JSONDB, alias_db: JSONDB) -> dict:
    logger.info("Building results...")
    results = {}
    for review in review_db.database:
        scores = review_db.get(review)
        final_score = 0
        for score in scores:
            final_score += score
        final_score = round(final_score / len(scores), 2)
        key = review + "|" + alias_db.get_key(review)
        results[key] = final_score
    return dict(sorted(results.items(), key=lambda item: item[1], reverse=True))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() == "pdf"
