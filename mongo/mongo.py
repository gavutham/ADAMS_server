def get_session_students(sessions_col, year, dep, sec):
    return sessions_col.find({"year": year, "department": dep, "section": sec})


def is_session_started(sessions_col, year, dep, sec):
    if sessions_col.count_documents({"year": year, "department": dep, "section": sec}, limit=1) > 0:
        return True
    else:
        return False