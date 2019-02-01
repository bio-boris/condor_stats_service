#!/usr/bin/env python3
import condor_statsClient

stats = condor_statsClient.condor_stats(url="http://localhost:5000/",
                                        token='7V72HVVLXTFD7QZN5XKEVZVVGBQXAXIG')

#print("Getting status")
#print(stats.status())

print("Getting queue_status")
print(stats.queue_status({}))

#print("Getting user prio")
#print(stats.conder_userprio_all({}))


print("Getting job_status")
print(stats.job_status({}))
