import pytz

from xgds_video import settings

TIME_ZONE = pytz.timezone(settings.XGDS_VIDEO_TIME_ZONE['code'])


def getShortTimeString(dateTime):
    return dateTime.strftime("%H:%M:%S")


def convertUtcToLocal(time):
    if time:
        time = time.replace(tzinfo=pytz.UTC)
        return time.astimezone(TIME_ZONE)
    else:
        return ""


def pythonDatetimeToJSON(pyDateTime):
    if pyDateTime:
        return {"year": pyDateTime.year, "month": pyDateTime.month, "day": pyDateTime.day,
                "hour": pyDateTime.hour, "min": pyDateTime.minute, "seconds": pyDateTime.second}
    else:
        return ""

'''
search and replace in file
pattern: regex pattern for searching
subst: string you want to replace with.
'''
def replace(file_path, pattern, subst):
    #create a temp file
    abs_path = mkstemp()
    new_file = open(str(abs_path[1]), 'w')
    old_file = open(file_path)
    for line in old_file:
        new_file.write(re.sub(pattern, subst, line))
    #close the temp file
    new_file.close()
    old_file.close()
    #remove the original file
    remove(file_path)
    #move the new file
    move(str(abs_path[1]), file_path)
