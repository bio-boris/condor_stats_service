#!/usr/bin/env python
from utils.CondorUtils import CondorQueueInfo

def main():
    cu = CondorQueueInfo()
    cu.save_queue_status()
    cu.save_user_prio()
    cu.save_job_status()


if __name__ == '__main__':
    main()
