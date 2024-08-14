import datetime

def time_for_exer_log():
    return datetime.datetime.now().strftime("%H:%M")

def date_for_exer_log():
    return str(datetime.date.today())

def now_for_logs():
    return datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
