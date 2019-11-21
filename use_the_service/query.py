from pprint import pprint

from installed_clients.condor_statsClient import condor_stats


def prRed(prt): print("\033[91m {}\033[00m".format(prt))


def prGreen(prt): print("\033[92m {}\033[00m".format(prt))


def prYellow(prt): print("\033[93m {}\033[00m".format(prt))


def prLightPurple(prt): print("\033[94m {}\033[00m".format(prt))


def prPurple(prt): print("\033[95m {}\033[00m".format(prt))


def prCyan(prt): print("\033[96m {}\033[00m".format(prt))


def prLightGray(prt): print("\033[97m {}\033[00m".format(prt))


def prBlack(prt): print("\033[98m {}\033[00m".format(prt))


# URL TAKEN FROM https://ci.kbase.us/#catalog/services
ci_url = "https://ci.kbase.us:443/dynserv/53c70d92f7830e2eb62f48171600ac56ebd090bd.condor-stats"
# URL TAKEN FROM https://narrative.kbase.us/#catalog/services
prod_url = "https://kbase.us:443/dynserv/53c70d92f7830e2eb62f48171600ac56ebd090bd.condor-stats"
url_of_stats_service = prod_url
my_token = "<YOUR_TOKEN_GOES_HERE>"

stats = condor_stats(url=url_of_stats_service, token=my_token)

queue_stats = stats.queue_status({})
user_prio = stats.condor_userprio_all({})
job_status = stats.job_status({})

"""
COMMENT OUT STUFF HOWEVER YOU"D LIKE

"""

prRed("=" * 50 + 'Queue Stats' + "=" * 50)
prRed("")
for i in queue_stats:
    prRed("=" * 50 + "{}".format(i) + "=" * 50)
    prRed(queue_stats[i])
    # pprint(queue_stats[i])

prYellow("=" * 50 + 'User Prios' + "=" * 50)
for i in user_prio:
    prYellow("=" * 50 + "{}".format(i) + "=" * 50)
    prYellow(user_prio[i])

prGreen("=" * 50 + 'Job Stats' + "=" * 50)

for row in job_status['rows']:
    prGreen("=" * 100)
    prYellow(row)
    pprint(row)

prLightGray(job_status.keys())
