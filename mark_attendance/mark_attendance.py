from flask import Flask, request

import time

def wait_for_login_threshold(year, dep, sec, sessions_col):
    # start_time = time.time()
    for i in range(4):
            students = list(sessions_col.find({"year": year, "department": dep, "section": sec}))
            if sum(stud["ready"] == True for stud in students) > 0.8 * len(students): # If > 80% students ready.
                return
            time.sleep(5)
    return # Timeout


    