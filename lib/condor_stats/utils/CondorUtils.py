import datetime
import json
import logging
import re
import subprocess
from configparser import ConfigParser

from collections import defaultdict

from bson import json_util
from pymongo import MongoClient

# Find a way to use authclient from installed_clients..
from .authclient import KBaseAuth

job_status_codes = {
    5: 'Held',
    4: 'Completed',
    3: 'Removed',
    2: 'Running',
    1: 'Idle',
    'U': 'Unexpanded',
    'E': 'Submission_error'
}


# TODO Get Condor QUeue Status
# Get number of slots and add it to `get_saved_queue_stats`

# Get Jobs

# self.save_job_status()
# self.save_user_prio()


class CondorQueueInfo:
    '''
    Used to generate queue info
    Used to save queue info info mongo
    Used for the IMPL to retrieve info from mongo
    '''

    def get_config(self):
        if self.config is None:
            self.config = self.load_config()
        return self.config

    def get_auth_client(self):
        if self.auth is None:
            config = self.config
            if 'auth-service-url' in config:
                auth_service_url = config['auth-service-url']
            else:
                auth_service_url = config['auth_service_url']
            self.auth = KBaseAuth(auth_service_url)
        return self.auth

    def get_username(self, ctx):
        return self.get_auth_client().get_user(ctx["token"])

    # There has to be a better way..
    def load_config(self):
        retconfig = {}
        config = ConfigParser()
        config.read("/kb/module/work/config.properties")
        for nameval in config.items('condor_stats' or 'global'):
            retconfig[nameval[0]] = nameval[1]
        retconfig['auth-service-url'] = retconfig['auth_service_url']
        return retconfig

    def __init__(self, config=None):
        self.config = config
        self.mc = MongoClient('mongodb://localhost:27017/')
        self.condor_q_db = self.mc['condor_q']

        self.queue_status = self.condor_q_db['queue_status']
        self.jobs = self.condor_q_db['jobs']
        self.user_prio = self.condor_q_db['user_prio']

        self.condor_q = None
        self.condor_user_prio_all = None
        self.auth = None



    def get_condor_q_data(self):
        if self.condor_q is None:
            self.condor_q = self._get_condor_q()
        return self.condor_q

    def get_condor_status_data(self):
        if self.condor_user_prio_all is None:
            self.condor_user_prio_all = self._get_user_prio_allusers()
        return self.condor_user_prio_all

    @staticmethod
    def _get_user_prio_allusers():
        command = 'condor_userprio -allusers'
        try:
            return {command: subprocess.check_output(command, shell=True).decode()}
        except subprocess.CalledProcessError:
            logging.error(f"Couldn't check {command}")

    @staticmethod
    def _get_condor_status():
        command = 'condor_status -json -attribute CLIENTGROUP,State,Name,Memory,Cpus'
        try:
            return json.loads(subprocess.check_output(command, shell=True).decode())
        except subprocess.CalledProcessError:
            logging.error(f"Couldn't check {command}")
        except json.JSONDecodeError:
            logging.error("Couldn't decode condor_status -json")

    @staticmethod
    def _get_condor_q():
        command = 'condor_q -json'
        try:
            return json.loads(subprocess.check_output(command, shell=True).decode())
        except subprocess.CalledProcessError:
            logging.error(f"Couldn't check {command}")
        except json.JSONDecodeError:
            logging.error("Couldn't decode condor_q -json")

    def _slot_stats(self):
        condor_status_data = self._get_condor_status()
        slots = defaultdict(lambda: defaultdict(int))

        for item in condor_status_data:
            cg = item['CLIENTGROUP']
            status = item['State']
            slots[cg]['total_slots'] += 1
            if status == 'Claimed':
                slots[cg]['used_slots'] += 1
            else:
                slots[cg]['free_slots'] += 1

        return slots

    @staticmethod
    def _get_client_group(job):
        try:
            return re.search('CLIENTGROUP == (".+?")', job['Requirements']).group(1).replace('"',
                                                                                             '')
        except AttributeError:
            return 'unknown'

    @staticmethod
    def _get_jobs_by_status(data):
        jobs = defaultdict(list)
        for item in data:
            jobstatus = job_status_codes[item['JobStatus']]
            jobs[jobstatus].append(item)
        return jobs

    # TODO REMOVE REGEX LOOKUP
    def _queue_stats(self,slot_stats):
        condor_q_data = self.get_condor_q_data()

        jobs_by_status = self._get_jobs_by_status(condor_q_data)
        client_groups = defaultdict(lambda: defaultdict(int))

        for status in jobs_by_status.keys():
            jobs = jobs_by_status[status]
            for job in jobs:
                if 'Requirements' in job:
                    client_group = self._get_client_group(job)
                    client_groups[client_group][status] += 1

        # Grab all clientgroups based on the queues
        # Add zeroed out stats for unavailable stats
        for cg in slot_stats.keys():
            for code in job_status_codes.values():
                if str(code) not in client_groups[cg]:
                    client_groups[cg][code] = 0

        return client_groups

    def save_user_prio(self):
        """
        Get the condor_userprio --all, save it to mongo.
        Old records deleted automatically based on index / created time
        :return:
        """
        get_user_prio_allusers = self._get_user_prio_allusers()
        get_user_prio_allusers['created'] = datetime.datetime.utcnow()
        self.user_prio.insert_one(get_user_prio_allusers)

    def save_queue_status(self):
        """
        Get the queue stats, save it to mongo.
        Old records deleted automatically based on index / created time
        """

        slot_stats = self._slot_stats()
        queue_stats = self._queue_stats(slot_stats)

        for cg in slot_stats.keys():
            queue_stats[cg]['total_slots'] = slot_stats[cg]['total_slots']
            queue_stats[cg]['free_slots'] = slot_stats[cg]['free_slots']
            queue_stats[cg]['used_slots'] = slot_stats[cg]['used_slots']

        queue_stats['created'] = datetime.datetime.utcnow()
        self.queue_status.insert_one(queue_stats)

    def save_job_status(self):
        """
        Get the queue job stats, save it to mongo.
        Old records deleted automatically based on index / created time
        :return:
        """
        condor_q_data = self.get_condor_q_data()
        fields = ['JobBatchName', 'ClusterId', 'AcctGroup', 'RemoteHost', 'kb_app_id',
                  'LastRejMatchReason', 'CLIENTGROUP']

        summary_keys = ['AcctGroup', 'ClusterId', 'JobBatchName', 'kb_app_id', 'QDate', 'JobStatus',
                        'kb_function_name', 'kb_module_name', 'CLIENTGROUP', 'RemoteHost',
                        'LastRejMatchReason']

        rows = []
        for job in condor_q_data:
            job_info = {}
            for key in summary_keys:
                job_info[key] = job.get(key, '')
            rows.append(job_info)

        condor_q_lookup = {'rows': rows,
                           'created': datetime.datetime.utcnow()}

        self.jobs.save(condor_q_lookup)

        # for job in condor_q_data:
        #     job_summary = {}
        #
        #     for key in summary_keys:
        #         if key == 'JobStatus':
        #             job_summary[key] = job_status[job[key]]
        #         else:
        #             job_summary[key] = job[key]
        #
        #     job_summary['client_group'] = get_client_group(job)
        #
        #     # if job_summary['AcctGroup'] != username:
        #     #     del job_summary['AcctGroup']
        #
        #     rows.append(job_summary)
        #
        # for job in condor_q_data:
        #     print(job)

    def get_last_record_mongo(self, collection):
        try:
            item = collection.find().limit(1).sort('created', -1)[0]
            item['_id'] = str(item['_id'])
            item['created'] = str(item['created'])
            return item
        except Exception as e:
            logging.error(e)
            return {'e': str(e)}

    def get_saved_queue_stats(self):
        """
        Look up the queue stats from mongo
        """
        return self.get_last_record_mongo(self.queue_status)

    # TODO ADMIN TOKEN TO SEE ALL
    # TODO NO TOKEN = NO USERNAMES
    def get_saved_job_stats(self, ctx):
        """
        Look up the job stats from mongo
        """

        username = self.get_username(ctx)

        jobs = self.get_last_record_mongo(self.jobs)
        for row in jobs['rows']:
            if row['AcctGroup'] != username:
                row['AcctGroup'] = ''

        return jobs

    #TODO AUTHENTICATION THIS OR PURGE THIS
    def get_saved_condor_userprio_all(self, ctx):
        """
        Look up the job stats from mongo
        """
        return self.get_last_record_mongo(self.user_prio)

# from bson import json_util
# from pymongo import MongoClient
# mc = MongoClient('mongodb://localhost:27017/')
# condor_q_db = mc['condor_q']
# queue_status = condor_q_db['queue_status']
# queue_status.find().limit(1).sort('created', -1)[0]


# #!/usr/bin/env python
# import argparse
# import json
# import os
# import re
# import subprocess
# import sys
# from collections import defaultdict
# import logging
#
# #TODO DECIDE IF YOU SHOULD CHANGE job status here or in JS.. Probably Here
# #TODO UNCOMMENT FILTER USERNAME
# #TODO ADD COLUMNS WITH TIMES
#
#
#
#
#
#
#
# def get_queue_stats(file=None):
#     """
#
#     :param file:
#     :return:
#     """
#     if file is not None:
#         condor_data = load_condor_q_from_file(file)
#     else:
#         condor_data = load_condor_q()
#
#     jobs_by_status = get_jobs_by_status(condor_data)
#
#     cg = defaultdict(lambda: defaultdict(int))
#
#     for status in jobs_by_status.keys():
#         jobs = jobs_by_status[status]
#
#         for job in jobs:
#             if 'Requirements' in job:
#                 client_group = get_client_group(job)
#                 cg[client_group][status] += 1
#
#     return cg
#
#
# def get_jobs_status(username, file=None):
#     """
#     Get filtered job status rows, filtered job status, and filtered by username
#     :param username: filter user jobs
#     :param file: Optional - use filename
#     :return:
#     """
#     if file is not None:
#         condor_data = load_condor_q_from_file(file)
#     else:
#         condor_data = load_condor_q()
#
#     rows = []
#
#     summary_keys = ['AcctGroup', 'ClusterId', 'JobBatchName',
#                     'kb_app_id', 'QDate', 'JobStatus', 'kb_function_name', 'kb_module_name']
#
#     for job in condor_data:
#         job_summary = {}
#
#         for key in summary_keys:
#             if key == 'JobStatus':
#                 job_summary[key] = job_status[job[key]]
#             else:
#                 job_summary[key] = job[key]
#
#         job_summary['client_group'] = get_client_group(job)
#
#         # if job_summary['AcctGroup'] != username:
#         #     del job_summary['AcctGroup']
#
#
#         rows.append(job_summary)
#
#     return rows
#
#
#
#
#
# def separator(f):
#     sep = "=" * 160
#     def wrap(*args, **kwargs):
#         print(sep)
#         return f(*args, **kwargs)
#     return wrap
#
# # TODO: Cache this
# def get_jobs_by_status(data):
#     jobs = defaultdict(list)
#     for item in data:
#         jobstatus = job_status[item['JobStatus']]
#         jobs[jobstatus].append(item)
#     return jobs
#
#
# def print_general_queue_status(jobs_by_status):
#     for status in jobs_by_status:
#         print("{}:{}".format(status, len(jobs_by_status[status])))
#
#
# def get_client_group(job):
#     try:
#         return re.search('CLIENTGROUP == (".+?")', job['Requirements']).group(1).replace('"', '')
#     except Exception:
#         return 'unknown'
#
# @separator
# def print_job_status_by_status():
#     print("Job Stats by Status")
#     jobs_by_status = get_jobs_by_status(json_data)
#
#     for status in jobs_by_status.keys():
#         jobs = jobs_by_status[status]
#
#         print("{}:{}".format(status, len(jobs_by_status[status])))
#
#         cg = defaultdict(int)
#
#         for job in jobs:
#             if 'Requirements' in job:
#                 client_group = get_client_group(job)
#                 cg[client_group] += 1
#
#         for c in cg:
#             print("\t{}:{}".format(c, cg[c]))
#
# @separator
# def print_job_status_by_client_group():
#     print("Job Stats by ClientGroup")
#     jobs_by_status = get_jobs_by_status(json_data)
#
#     cg = defaultdict(lambda: defaultdict(int))
#
#     for status in jobs_by_status.keys():
#         jobs = jobs_by_status[status]
#
#         for job in jobs:
#             if 'Requirements' in job:
#                 client_group = get_client_group(job)
#                 cg[client_group][status] += 1
#
#     for c in cg:
#         print("{}:{}".format(str(c), dict(cg[c])))
#
#
# def load_condor_q_from_file(file):
#     with open(file) as f:
#         return json.load(f)
#
#
# def look_for_condor_container():
#     cmd = "docker ps | grep kbase/condor | cut -f1 -d' '"
#     lines = subprocess.check_output(cmd, shell=True).decode().split("\n")
#
#     names = []
#     for line in lines:
#         if len(line) > 2:
#             names.append(line)
#
#     if len(names) > 1:
#         raise Exception("Found too many container names" + str(names))
#     elif len(names) == 0 :
#         raise Exception("Couldn't find any docker containers for condor")
#     else:
#         return str(names[0])
#
#
# def load_condor_q():
#     if cmd_exists('condor_q'):
#         comm = ['condor_q', '-json']
#         output = subprocess.check_output(comm, shell=True).decode()
#         return json.loads(output)
#     else:
#         container_id = look_for_condor_container()
#         comm = " ".join(['docker', 'exec', '-it', '-u', '0', container_id, 'condor_q', '-json'])
#         output = subprocess.check_output(comm, shell=True).decode()
#         return json.loads(output)
#
#
# def cmd_exists(cmd):
#     return any(
#         os.access(os.path.join(path, cmd), os.X_OK)
#         for path in os.environ["PATH"].split(os.pathsep)
#     )
#
#
# def print_table(table):
#     longest_cols = [
#         (max([len(str(row[i])) for row in table]) + 3)
#         for i in range(len(table[0]))
#     ]
#     row_format = "".join(["{:>" + str(longest_col) + "}" for longest_col in longest_cols])
#     for row in table:
#         print(row_format.format(*row))
#
# @separator
# def display_job_info(status='Idle', fields=None):
#     jobs_by_status = get_jobs_by_status(json_data)
#
#     if fields is None:
#         fields = ['JobBatchName', 'ClusterId', 'AcctGroup', 'RemoteHost', 'kb_app_id',
#                   'LastRejMatchReason']
#
#     print_lines = []
#     for job in jobs_by_status[status]:
#         line = []
#
#         for field in fields:
#             if field in job:
#                 line.append("{}".format(job[field]))
#             else:
#                 line.append("")
#
#         line.append(get_client_group(job))
#         print_lines.append(line)
#
#     fields.append("ClientGroup")
#
#     print_lines.insert(0, fields)
#     print(print_table(print_lines))
#
#
# def display_idle_jobs():
#     display_job_info('Idle')
#
#
# def display_running_jobs():
#     display_job_info('Running')
#
#
# def display_removed_jobs():
#     display_job_info('Removed')
#
#
# def display_held_jobs():
#     display_job_info('Held')
#
#
# def display_completed_jobs():
#     display_job_info('Completed')
#
#
# if __name__ == '__main__':
#     parser = argparse.ArgumentParser(description='See info extracted from condor_q')
#     parser.add_argument('--file', help='Specify output file from condor_q -json')
#     parser.add_argument('--status', action='store_true', help='Get status of all jobs')
#     parser.add_argument('--status_client_group', action='store_true',
#                         help='Get status of all queues')
#     parser.add_argument('--idle', action='store_true', help='Get status of all idle jobs')
#     parser.add_argument('--running', action='store_true', help='Get status of all running jobs')
#     parser.add_argument('--removed', action='store_true', help='Get status of all removed jobs')
#     parser.add_argument('--held', action='store_true', help='Get status of all held jobs')
#     parser.add_argument('--completed', action='store_true', help='Get status of all completed jobs')
#
#     args = parser.parse_args()
#
#     if args.file:
#         json_data = load_condor_q_from_file(args.file)
#     else:
#         json_data = load_condor_q()
#
#     if args.status:
#         print_job_status_by_status()
#     if args.status_client_group:
#         print_job_status_by_client_group()
#     if args.idle:
#         display_idle_jobs()
#     if args.running:
#         display_running_jobs()
#     if args.removed:
#         display_removed_jobs()
#     if args.held:
#         display_held_jobs()
#     if args.completed:
#         display_completed_jobs()
#
# #TODO Cache call to condor_q
# #TODO Figure out why None is being printed
