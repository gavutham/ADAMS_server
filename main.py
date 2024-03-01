# Importing flask module in the project is mandatory
# An object of Flask class is our WSGI application.
from flask import Flask, request, make_response
from fire_base import firebase_server
from mark_attendance import mark_attendance

import time

at_dict = dict()
pp_list = dict()

app = Flask(__name__)

@app.route('/')
def hello_world():
    #have to give the variables to the display _students dynamically in post request
    std = firebase_server.display_students('I','MECH','A')
    return std


@app.route("/<year>/<dep>/<sec>", methods=["GET"])
def get_students(year, dep, sec):
    return at_dict.get("{}{}{}".format(year, dep, sec), 403)
    # std = firebase_server.display_students(year, dep, sec)
    # return std


@app.route("/get-student-uuid/<year>/<dep>/<sec>/<email>", methods=["GET"])
def get_student_uuid(year, dep, sec, email):
    # std = firebase_server.display_students(year, dep, sec)
    # x = dict()
    # for i in std:
    #     if i.get("email") == email:
    #         x = i
    #         break
    std_data = at_dict.get("{}{}{}".format(year, dep, sec), None)
    if not(std_data):
        return 403
    else:
        for i in std_data:
            if i["email"] == email:
                return str(i["uuid"]), 200
        return "Student not found!", 404


# Top level function - TEACHER APP
@app.route("/start-session/<year>/<dep>/<sec>")
def start_session(year, dep, sec):
    if (year+dep+sec in at_dict):
        return "Session already started!", 404
    session_students = firebase_server.generate_sec_uuids(year, dep, sec)
    at_dict[year+dep+sec] = session_students
    mark_attendance.wait_for_login_threshold(year, dep, sec, at_dict) # Waits until 80% threshold reached.
    # mark_attendance.pp_start_session(year, dep, sec)
    ready_uuids = (i["uuid"] for i in at_dict[year+dep+sec] if (i["ready"]) == True) # Only ready.
    return ready_uuids
    # return at_dict # for testing


@app.route("/stop-session/<year>/<dep>/<sec>")
def stop_session(year, dep, sec):
    if (year+dep+sec):
        del at_dict[year+dep+sec]
        return "Session stopped!", 200
    else:
        return "Session not started yet!", 404


# @app.route("/pp-verify/<year>/<dep>/<sec>/<email>")
# def pp_verify(year, dep, sec, email):
#     if not (year+dep+sec in at_dict):
#         return "Session not started yet!", 403;
#     else:
#         students = at_dict[year+dep+sec]
#         for i in students:
#             if (i["email"] == email):
#                 i["pp_verify"] = True;
#         print(at_dict)
#         resp = make_response("PP Verified", 200)
#         resp.set_cookie('email', email)
#         return resp


# Student app
@app.route("/ready/<year>/<dep>/<sec>/<email>")
def ready(year, dep, sec, email):
    if not (year+dep+sec) in at_dict:
        return "Session not started!", 403
    for i in at_dict[year+dep+sec]:
        if (i["email"] == email):
            i["ready"] = True
    return "Ready status marked.", 200


@app.route("/pp-status-verify/<year>/<dep>/<sec>/<email>")
def pp_status_verify(year, dep, sec, email):
    if not (year+dep+sec) in at_dict:
        return "Session not started!", 403
    for i in at_dict[year+dep+sec]:
        if (i["email"] == email):
            if i["pp_verify"] == True:
                return True, 200
    return False, 200


# PP-VERIFY - Accessed by teacher at the first. Then accessed by students.
@app.route("/pp-verify/<year>/<dep>/<sec>", methods=["POST"])
def pp_verify(year, dep, sec):
    if not (year+dep+sec) in at_dict:
        return "Session not started!", 403
    req = request.get_json()

    # Parse req body. Get all UUIDS from teacher scan.
    req_pp_list = [] # list of dictionaries with keys uuid and rssi parsed from request.
    pp_list[year+dep+sec] = [] # Contains UUIDs for pp verification.

    # Parse and add to pp_list
    pp_top5 = sorted(req_pp_list, key=lambda i: i['rssi'])[:5]
    pp_list[year+dep+sec].update(req_pp_list)
    # Set pp_verify = True for closest 5 students.
    return 200


# @app.route("/test-time/<timeout>")
# def test_timeout(timeout):
#     time.sleep(int(timeout))
#     return "Success. We waited for {} seconds!".format(timeout), 200;


if __name__ == '__main__':
    app.run(host='0.0.0.0', )