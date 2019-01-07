#!/usr/bin/env python3
from condor_statsClient import *


stats = condor_stats(url="http://localhost:10001/",token='7V72HVVLXTFD7QZN5XKEVZVVGBQXAXIG')




print(stats.status())

print(stats.queue_status({}))