#!/usr/bin/env python
from datetime import datetime

from utils.CondorUtils import CondorQueueInfo

"""
This script dumps the current state of condor into the data store
"""


def main():
    cu = CondorQueueInfo()
    cu.save_queue_status()
    cu.save_user_prio()
    cu.save_job_status()
    time = datetime.utcnow()
    # print("Generated condor dump at: " + str(time))


if __name__ == '__main__':
    main()
