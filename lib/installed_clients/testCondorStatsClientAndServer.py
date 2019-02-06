#!/usr/bin/env python3
import condor_statsClient

#stats = condor_statsClient.condor_stats(url="http://localhost:5000/", token='7V72HVVLXTFD7QZN5XKEVZVVGBQXAXIG')

url = "http://localhost:5000/"
#url = "https://ci.kbase.us:443/dynserv/05e92d1b3477fe72f6f4ca18eedd25fb7dca9a23.condor-stats"
stats = condor_statsClient.condor_stats(url=url,
					token='7V72HVVLXTFD7QZN5XKEVZVVGBQXAXIG')

#
# #print("Getting status")
# #print()
#
# print("Getting queue_status")
# print()
#
# #print("Getting user prio")
# #print()
#
#
# print("Getting job_status")
# print(stats.job_status({}))

status = stats.status()

queue_stats = stats.queue_status({})

user_prio = stats.condor_userprio_all({})

job_status = stats.job_status({})


#print("=" * 50 + 'Queue Stats' + "=" * 50)
#print("")
#for i in queue_stats:
#	print("="* 50 + "{}".format(i) + "="*50)
#	print(queue_stats[i])
#
#print("=" * 50 + 'User Prios' + "=" * 50)
#for i in user_prio:
#	print("="* 50 + "{}".format(i) + "="*50)
#	print(user_prio[i])
#
#
#print("=" * 50 + 'Job Stats' + "=" * 50)

#for row in job_status['rows']:
#	print("="* 100 )
#	print(row)

print(job_status.keys())
