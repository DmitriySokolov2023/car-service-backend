from datetime import datetime

def school_working_year():
    if (datetime.now().month < 8): return datetime.now().year - 1
    return datetime.now().year
