from flask import Flask, request

import time

def wait_for_login_threshold(year, dep, sec, at_dict):
    # start_time = time.time()
    for i in range(4):
            if sum(stud["ready"] == True for stud in at_dict[year+dep+sec])\
                > 0.8 * len(at_dict[year+dep+sec]): # If > 80% students ready.
                 return
            time.sleep(5)
    return # Timeout


    