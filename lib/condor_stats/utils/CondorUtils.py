import datetime
import json
import logging
import os
import re
import subprocess
from collections import defaultdict
from configparser import ConfigParser
from typing import Dict

from pymongo import MongoClient

# Find a way to use authclient/catalog from installed_clients instead of copying them?
from .CatalogClient import Catalog
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


# TODO Create a human readable job status code
# TODO Create a human readable "Queue Time", "Job Run Time"
# TODO Create mongo trigger
# TODO See how many jobs are ahead of yours for the given client group
# TODO FILTER OUT COMPLETED FROM JOBS LIST
# TODO JOBS BY FUNCTION


# IF JOB STATUS is NOT 2, APPEND QUEUED JOBS.. Jobs AHEAD of yours


class CondorQueueInfo:
    '''
    Used to generate queue info
    Used to save queue info info mongo
    Used for the IMPL to retrieve info from mongo
    '''

    def get_config(self) -> dict:
        if self.config is None:
            self.config = self.load_config()
        return self.config

    def get_auth_client(self) -> KBaseAuth:
        if self.auth is None:
            auth_service_url = self.config['auth-service-url']
            self.auth = KBaseAuth(auth_service_url)
        return self.auth

    def get_catalog_client(self, ctx) -> Catalog:
        if self.catalog_client is None:
            catalog_service_url = self.config['kbase-endpoint'] + "/catalog"
            self.catalog_client = Catalog(url=catalog_service_url, token=ctx['token'])
        return self.catalog_client

    def get_username(self, ctx) -> str:
        if self.username is None:
            self.username = self.get_auth_client().get_user(ctx["token"])
        return self.username

    def is_admin(self, ctx) -> bool:
        """
        Check to see if the user is an admin, as per defined in the ENV secure
        :return:
        """
        username = self.get_username(ctx)
        cc = self.get_catalog_client(ctx)
        return cc.is_admin(username)

    # There has to be a better way..
    @staticmethod
    def load_config() -> dict:
        retconfig = {}
        config = ConfigParser()
        config.read("/kb/module/deploy.cfg")

        heading = 'condor_stats'
        if 'global' in config.keys():
            heading = 'global'

        for nameval in config.items(heading):
            retconfig[nameval[0]] = nameval[1]

        return retconfig

    def __init__(self, config=None):
        self.config = config
        self.mc = MongoClient('mongodb://localhost:27017/')
        self.condor_db = self.mc['condor']

        self.queue_status = self.condor_db['queue_status']
        self.jobs = self.condor_db['jobs']
        self.user_prio = self.condor_db['user_prio']

        self.username = None

        expire_after_seconds = os.environ.get(
            "KBASE_SECURE_CONFIG_PARAM_RECORD_EXPIRY_TIME_SECONDS", 120)

        self.queue_status.ensure_index("created", expireAfterSeconds=expire_after_seconds)
        self.jobs.ensure_index("created", expireAfterSeconds=expire_after_seconds)
        self.user_prio.ensure_index("created", expireAfterSeconds=expire_after_seconds)

        self._condor_q = None
        self._condor_user_prio_all = None
        self._queue_stats = None
        self.auth = None
        self.catalog_client = None
        self._slot_stats = None
        self._discovered_client_groups = defaultdict(int)

    def get_slot_stats(self) -> dict:
        if self._slot_stats is None:
            self._slot_stats = self._gen_slot_stats_partionable()
        return self._slot_stats

    def get_queue_stats(self) -> dict:
        if self._queue_stats is None:
            self._queue_stats = self._gen_queue_stats()
        return self._queue_stats

    def get_condor_q_data(self) -> dict:
        if self._condor_q is None:
            self._condor_q = self._get_condor_q()
        return self._condor_q

    def get_condor_status_data(self) -> dict:

        if self._condor_user_prio_all is None:
            self._condor_user_prio_all = self._get_user_prio_allusers()
        return self._condor_user_prio_all

    @staticmethod
    def _get_user_prio_allusers() -> dict:
        command = 'condor_userprio -allusers'
        try:
            return {command: subprocess.check_output(command, shell=True).decode()}
        except subprocess.CalledProcessError:
            logging.error(f"Couldn't check {command}")

    @staticmethod
    def _get_condor_status() -> dict:
        command = 'condor_status -json -attribute CLIENTGROUP,State,Name,Memory,Cpus'
        try:
            return json.loads(subprocess.check_output(command, shell=True).decode())
        except subprocess.CalledProcessError:
            logging.error(f"Couldn't check {command}")
        except json.JSONDecodeError:
            logging.error("Couldn't decode condor_status -json")

    @staticmethod
    def _get_condor_status_partionable() -> dict:
        command = 'condor_status -constraint \'SlotType == "Partitionable"\' -json -attributes cpus,totalcpus,CLIENTGROUP,state,name,totalmemory,memory,disk,totaldisk'
        try:
            return json.loads(subprocess.check_output(command, shell=True).decode())
        except subprocess.CalledProcessError:
            logging.error(f"Couldn't check {command}")
        except json.JSONDecodeError:
            logging.error("Couldn't decode condor_status -json")

    @staticmethod
    def _get_condor_q() -> dict:
        command = 'condor_q -json'
        try:
            return json.loads(subprocess.check_output(command, shell=True).decode())
        except subprocess.CalledProcessError:
            logging.error(f"Couldn't check {command}")
        except json.JSONDecodeError:
            logging.error("Couldn't decode condor_q -json")

    def _gen_slot_stats_partionable(self) -> dict:
        """
        Calculate number of cpus in use versus available per queue
        :return:
        """
        condor_status_data = self._get_condor_status_partionable()
        slots = defaultdict(lambda: defaultdict(int))  # type: Dict[str, Dict[str, int]]

        for item in condor_status_data:
            cg = item['CLIENTGROUP']
            total_cpus = item['totalcpus']
            cpus_left = item['cpus']
            cpus_in_use = total_cpus - cpus_left
            slots[cg]['total_slots'] += total_cpus
            slots[cg]['used_slots'] += cpus_in_use
            slots[cg]['free_slots'] += cpus_left

        return slots

    def _gen_slot_stats(self) -> dict:
        condor_status_data = self._get_condor_status()
        slots = defaultdict(lambda: defaultdict(int))  # type: Dict[str, Dict[str, int]]

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
    def _get_client_group(job) -> str:
        try:
            return re.search('CLIENTGROUP == (".+?")', job['Requirements']).group(1).replace('"',
                                                                                             '')
        except AttributeError:
            return 'unknown'

    @staticmethod
    def _get_jobs_by_status(data) -> defaultdict(list):
        jobs = defaultdict(list)
        for item in data:
            jobstatus = job_status_codes[item['JobStatus']]
            jobs[jobstatus].append(item)
        return jobs

    # TODO REMOVE REGEX LOOKUP
    def _gen_queue_stats(self) -> dict:
        condor_q_data = self.get_condor_q_data()
        jobs_by_status = self._get_jobs_by_status(condor_q_data)
        client_groups = defaultdict(lambda: defaultdict(int))

        for status in jobs_by_status.keys():
            jobs = jobs_by_status[status]
            for job in jobs:
                if 'Requirements' in job:
                    client_group = self._get_client_group(job)
                    client_groups[client_group][status] += 1

        return client_groups

    @staticmethod
    def _get_last_record_mongo(collection) -> dict:
        try:
            item = collection.find().limit(1).sort('created', -1)[0]
            item['_id'] = str(item['_id'])
            item['created'] = str(item['created'])
            return item
        except Exception as e:
            logging.error(e)
            return {'e': str(e),
                    'msg': 'no records are available for collection:' + collection.name}

    def get_saved_queue_stats(self) -> dict:
        """
        Look up the queue stats from mongo
        """
        return self._get_last_record_mongo(self.queue_status)

    def get_saved_job_stats(self, ctx) -> dict:
        """
        Look up the job stats from mongo. If the user is not an admin, remove usernames from the list
        """
        jobs = self._get_last_record_mongo(self.jobs)

        if self.is_admin(ctx):
            return jobs

        username = self.get_username(ctx)

        if 'rows' in jobs:
            for row in jobs['rows']:
                if row['AcctGroup'] != username:
                    row['AcctGroup'] = ''

        return jobs

    # TODO AUTHENTICATION THIS OR PURGE THIS
    def get_saved_condor_userprio_all(self, ctx) -> dict:
        """
        Look up the job stats from mongo
        """
        if not self.is_admin(ctx):
            return {'msg': 'Sorry you are not condor_stats admin'}

        return self._get_last_record_mongo(self.user_prio)

    def save_user_prio(self) -> None:
        """
        Get the condor_userprio --all, save it to mongo.
        Old records deleted automatically based on index / created time
        :return:
        """

        get_user_prio_allusers = self._get_user_prio_allusers()
        get_user_prio_allusers['created'] = datetime.datetime.utcnow()
        self.user_prio.insert_one(get_user_prio_allusers)

    def save_queue_status(self) -> None:
        """
        Get the queue stats, save it to mongo.
        Old records deleted automatically based on index / created time
        """

        slot_stats = self.get_slot_stats()
        queue_stats = self.get_queue_stats()

        # Grab all clientgroups based on the jobs and slots currently in the queue
        # Add zeroed out stats for unavailable stats
        all_keys = set().union(queue_stats.keys(), slot_stats.keys())
        for cg in all_keys:
            for code in job_status_codes.values():
                if str(code) not in queue_stats[cg]:
                    queue_stats[cg][code] = 0

        for cg in all_keys:
            for header in ['total_slots', 'free_slots', 'used_slots']:
                queue_stats[cg][header] = 0
                if header in slot_stats[cg]:
                    queue_stats[cg][header] = slot_stats[cg][header]

        queue_stats['created'] = datetime.datetime.utcnow()
        self.queue_status.insert_one(queue_stats)

    def save_job_status(self) -> None:
        """
        Get the queue job stats, save it to mongo.
        Old records deleted automatically based on index / created time
        :return:
        """
        condor_q_data = self.get_condor_q_data()

        summary_keys = ['AcctGroup', 'AccountingGroup', 'ClusterId', 'JobBatchName', 'kb_app_id',
                        'QDate', 'JobStartDate', 'JobCurrentStartDate',
                        'JobCurrentStartExecutingDate', 'RemoteWallClockTime',
                        'CpusProvisioned', 'CPUsUsage', 'CumulativeRemoteSysCpu',
                        'CumulativeRemoteUserCpu', 'MemoryUsage', 'JobStatus',
                        'kb_function_name', 'kb_module_name', 'CLIENTGROUP', 'RemoteHost',
                        'LastRejMatchReason']

        queue_stats = self.get_queue_stats()

        rows = []
        for job in condor_q_data:
            job_info = {}

            for key in summary_keys:
                job_info[key] = job.get(key, '')

            if job_info['JobStatus'] == 4:
                continue

            job_info["AcctGroup"] = job_info["AccountingGroup"]
            del job_info["AccountingGroup"]

            job_info['CLIENTGROUP'] = self._get_client_group(job)
            cg = job_info['CLIENTGROUP']

            # Find jobs ahead for queued jobs
            job_info['JobsAhead'] = 0
            if job_info['JobStatus'] == 1:
                job_info['JobsAhead'] = queue_stats[cg]['Idle']

            # Possibly remove these to save space in json return object
            job_info['QDateHuman'] = str(datetime.datetime.utcfromtimestamp(job_info['QDate']))
            job_info['JobStatusHuman'] = job_status_codes[job_info['JobStatus']]

            for key in job_info:
                job_info[key] = str(job_info[key])

            rows.append(job_info)

        condor_q_lookup = {'rows': rows,
                           'created': datetime.datetime.utcnow()}

        self.jobs.save(condor_q_lookup)
