#!/usr/bin/env python3
import condor_statsClient


def prRed(prt): print("\033[91m {}\033[00m".format(prt))


def prGreen(prt): print("\033[92m {}\033[00m".format(prt))


def prYellow(prt): print("\033[93m {}\033[00m".format(prt))


def prLightPurple(prt): print("\033[94m {}\033[00m".format(prt))


def prPurple(prt): print("\033[95m {}\033[00m".format(prt))


def prCyan(prt): print("\033[96m {}\033[00m".format(prt))


def prLightGray(prt): print("\033[97m {}\033[00m".format(prt))


def prBlack(prt): print("\033[98m {}\033[00m".format(prt))


# stats = condor_statsClient.condor_stats(url="http://localhost:5000/", token='7V72HVVLXTFD7QZN5XKEVZVVGBQXAXIG')

url = "http://localhost:5000/"
# url = "https://ci.kbase.us:443/dynserv/05e92d1b3477fe72f6f4ca18eedd25fb7dca9a23.condor-stats"
token = ''
stats = condor_statsClient.condor_stats(url=url,
                                        token=token)

status = stats.status()

queue_stats = stats.queue_status({})

user_prio = stats.condor_userprio_all({})

job_status = stats.job_status({})

prRed("=" * 50 + 'Queue Stats' + "=" * 50)
prRed("")
for i in queue_stats:
    prRed("=" * 50 + "{}".format(i) + "=" * 50)
    prRed(queue_stats[i])

prYellow("=" * 50 + 'User Prios' + "=" * 50)
for i in user_prio:
    prYellow("=" * 50 + "{}".format(i) + "=" * 50)
    prYellow(user_prio[i])

prGreen("=" * 50 + 'Job Stats' + "=" * 50)

for row in job_status['rows']:
    prGreen("=" * 100)
    prYellow(row)

prLightGray(job_status.keys())
