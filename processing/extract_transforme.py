import re 

"""
in : list of rows 
out : dateTime,ip,country,Succes,Failed,Invalid user for sshd service
"""
pattern = re.compile(r'(?P<month>\w{3})\s+(?P<day>\d{1,2})\s(?P<time>\d{2}:\d{2}:\d{2})\s(?P<server>\S+)\s(?P<service>\w+)\[.+:\s+(?P<message>.+)')


def exctract_from_row(row):
    if not row or not isinstance(row, str):
        return None
    match = re.search(pattern, row)
    if match:
        return match.groupdict()
    return None