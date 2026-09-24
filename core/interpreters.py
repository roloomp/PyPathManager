import subprocess
import re


def get_interpreters():
    result = subprocess.run(["py", "-0p"], capture_output=True, text=True)
    return result.stdout

def parsing_interpreters(interpreters):
    all_interpreters = list(interpreters.splitlines())
    all_interpreters = [re.sub(r' +', ' ', i)[1:] for i in all_interpreters]
    all_interpreters = [i[3:] for i in all_interpreters if i[:3] == "-V:"]
    all_interpreters = [re.match(r'(\S+)\s+(\*)?\s*(.+)', i).groups() for i in all_interpreters]
    return all_interpreters
