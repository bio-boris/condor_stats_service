#!/usr/bin/env python
from utils.CondorUtils import CondorQueueInfo
from datetime import datetime

def main():
    cu = CondorQueueInfo()
    cu.save_queue_status()
    cu.save_user_prio()
    cu.save_job_status()
    time = datetime.utcnow()
    # print("Generated condor dump at: " + str(time))


if __name__ == '__main__':
    main()
