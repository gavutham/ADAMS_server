# Importing flask module in the project is mandatory
# An object of Flask class is our WSGI application.
import requests
from flask import Flask, request, make_response, jsonify
from fire_base import firebase_server
from fire_base.firebase_server import set_attendance_data, set_attendance_flag
from mark_attendance import mark_attendance
from mongo import mongo
from pymongo import MongoClient
import threading 
import time


client = MongoClient('localhost', 27017)

db = client["adams_server_db"]
sessions_col = db["sessions"]
beacons_col = db["beacons"]
pp_status_col = db["pp_status"]

app = Flask(__name__)


@app.route('/')
def hello_world():
    return "Hello world!"


@app.route("/<year>/<dep>/<sec>", methods=["GET"])
def get_students(year, dep, sec):
    return mongo.get_session_students(sessions_col, year, dep, sec), 200


@app.route("/get-student-uuid/<year>/<dep>/<sec>/<email>", methods=["GET"])
def get_student_uuid(year, dep, sec, email):
    std_data = mongo.get_session_students(sessions_col, year, dep, sec)
    if not(std_data):
        return 403
    else:
        for i in std_data:
            if i["email"] == email:
                sessions_col.update_one({"email": email}, {"$set": {"ready": True}})
                return str(i["uuid"]), 200
        return "Student not found!", 404


# Top level function - TEACHER APP
@app.route("/start-session/<year>/<dep>/<sec>")
def start_session(year, dep, sec):
    timeout_thread = threading.Thread(target=stop_session_thread, args=(year, dep, sec))
    timeout_thread.start()
    if mongo.is_session_started(sessions_col, year, dep, sec):
        return "Session already started!", 404
    session_students = firebase_server.generate_sec_uuids(year, dep, sec)
    sessions_col.insert_many(session_students)
    mark_attendance.wait_for_login_threshold(year, dep, sec, sessions_col) # Waits until 80% threshold reached.
    # mark_attendance.pp_start_session(year, dep, sec)
    ready_uuids = [i["uuid"] for i in
                   mongo.get_session_students(sessions_col, year, dep, sec)
                   if (i["ready"]) == True] # Only ready.
    return jsonify(ready_uuids), 200
    # return "Done!", 200
    # return at_dict # for testing


def stop_session_thread(year, dep, sec):
    time.sleep(180)
    stop_session(year, dep, sec)


@app.route("/stop-session/<year>/<dep>/<sec>")
def stop_session(year, dep, sec):
    sessions_col.update_many({"pp_verify": True}, {"$set": {"att_verified": True}})
    if mongo.is_session_started(sessions_col, year, dep, sec):
        std_data = mongo.get_session_students(sessions_col, year, dep, sec)
        print("\nSTOPPING SESSION!\n")
        present = []
        absent = []
        for i in std_data:
            if i["att_verified"]:
                present.append(i["email"])
            else:
                absent.append(i["email"])
        
        print("\nPRESENT:\n")
        print(present)
        print("\nABSENT\n")
        print(absent)
        sessions_col.delete_many({"year": year, "department": dep, "section": sec})

        set_attendance_data(year, dep, sec, present, absent) #store the result in firebase
        set_attendance_flag(year, dep, sec, False)
        
        return "Session stopped!", 200
    else:
        return "Session not started yet!", 404

@app.route("/is-session-started/<year>/<dep>/<sec>")
def is_session_started(year, dep, sec):
    if mongo.is_session_started(sessions_col, year, dep, sec):
        return "true";
    else:
        return "false";


@app.route("/post-beacon-details/<ip>/<classroom>", methods=["POST"])
def post_beacon_details(ip, classroom):
    beacons_col.replace_one({"ip": ip}, {"ip": ip, "classroom": classroom}, upsert=True) # init beacon.
    return "Done!", 200


@app.route("/pp-status-verify/<year>/<dep>/<sec>/<email>")
def pp_status_verify(year, dep, sec, email):
    if not mongo.is_session_started(sessions_col, year, dep, sec):
        return "Session not started!", 403
    else:
        student = sessions_col.find_one({"year": year, "department": dep, "section": sec, "email": email})
        if student["pp_verify"] == True:
            return "true", 200
        else:
            return "false", 200


# PP-VERIFY - Accessed by teacher at the first. Then accessed by students.
@app.route("/pp-verify/<year>/<dep>/<sec>", methods=["POST"])
def pp_verify(year, dep, sec):
    yds = year+dep+sec
    if not mongo.is_session_started(sessions_col, year, dep, sec):
        return "Session not started!", 403
    req = request.get_json()
    pp_status_col.insert_one({"classroom": yds}, {"classroom": yds, "scan_details": req})
    print(req)

    req_pp_list = list(req) # list of dictionaries with keys uuid and rssi parsed from request.
    std_data = mongo.get_session_students(sessions_col, year, dep, sec)
    std_uuids = [i["uuid"] for i in std_data]
    print("STD UUIDS:")
    print(std_uuids)

    # Parse and add to pp_list
    pp_valid = [i for i in req_pp_list if i["uuid"] in std_uuids]
    pp_sorted = sorted(pp_valid, key=lambda i: i["rssi"], reverse=True)

    count = 0;
    pp_top = []
    for i in pp_sorted:
        # att_verified = True is hardcoded. Should happen only after both bb-verify and face-auth is done.
        # sessions_col.update_one({"uuid": i["uuid"]}, {"$set": {"pp_verify": True, "att_verified": True}})
        result = sessions_col.update_one({"uuid": i["uuid"], "bb_rssi": {"$lt": i["rssi"]}}, {"$set": {"pp_verify": True}})
        sessions_col.update_one({"uuid": i["uuid"], "pp_rssi": {"$lt": i["rssi"]}}, {"$set": {"pp_rssi": i["rssi"]}})
        if result.matched_count > 0:
            pp_top.append(i)
            count += 1
            if count >= 2:
                break;

    # for i in pp_sorted:
    #     sessions_col.update_one({"uuid": i["uuid"], "pp_rssi": {"$gt": i["rssi"]}}, {"$set": {"pp_rssi": i["rssi"]}})
    # pp_list[year+dep+sec].update(req_pp_list)
    # Set pp_verify = True for closest 5 students.
    return pp_top, 200


def pp_avg_rssi(year, dep, sec):
    yds = year+dep+sec
    pp_lists = pp_status_col.find({"classroom": yds})


@app.route("/get-beacon-ips/<year>/<dep>/<sec>", methods=["GET"])
def get_beacon_ips(year, dep, sec):
    yds = year+dep+sec
    ips = [i["ip"] for i in beacons_col.find({"classroom": {"$regex": yds}})]
    # print(ips)
    return jsonify(ips)
    # for ip in ips:
        # resp = requests.get("http://"+ip+"/ble_scan")
        # print(str(resp))


@app.route("/bb-verify/<year>/<dep>/<sec>", methods=["POST"])
def bb_verify(year, dep, sec):
    req = request.get_json()
    # req = json.loads(req)
    print(req)
    # return "Done!", 200
    for scan in req:
        scan_results = scan["scan_results"]
        for device in scan_results:
            print(device)
            sessions_col.update_one({"uuid": device["uuid"].lower(), "bb_rssi": {"$lt": device["rssi"]}}, {"$set": {"bb_rssi": device["rssi"]}}) # If beacon says too close.
            # sessions_col.update_one({"uuid": device["uuid"].lower(), "$and": [{"pp_rssi": {"$lt": device["rssi"]}}, {"pp_rssi": {"$ne": float('inf')*-1}}]}, {"$set": {"bb_verify": False}})
            # print("BB VERIFY (FALSE): ", device["uuid"].lower())
    print("Req: ", req)
    return "Done!", 200



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
    # app.run(host='144.91.106.164', port=8000, debug=True)
