#!/usr/bin/env python

import logging
import os
from utils.CondorUtils import CondorQueueInfo


logging.info("About to setup condor")
condor_config_dir = "/etc/condor"
os.makedirs(condor_config_dir, exist_ok=True)

config_file = "{}/condor_config".format(condor_config_dir)
password_file = "{}/password".format(condor_config_dir)
password_binary = "/usr/sbin/condor_store_cred"

config = CondorQueueInfo.load_config()

environments = {'https://ci.kbase.us/services': 'CI',
                'https://next.kbase.us/services': 'NEXT',
                'https://appdev.kbase.us/services': 'APPDEV',
                'https://kbase.us/services': 'PROD'}

endpoint = config.get('kbase-endpoint', config.get('kbase_endpoint'))
env = environments[endpoint]

schedd_host = os.environ.get(f"KBASE_SECURE_CONFIG_PARAM_SCHEDD_HOST_{env}", "kbase@ci-dock")
condor_host = os.environ.get(f"KBASE_SECURE_CONFIG_PARAM_CONDOR_HOST_{env}", "ci.kbase.us:9618")

password_env = f"KBASE_SECURE_CONFIG_PARAM_POOL_PASSWORD_{env}"
password = os.environ.get(password_env, None)

if password is None:
    raise Exception(f"Password not found in environment. Checked {password_env}")

if not os.path.isfile(config_file):
    logging.info("About to write config file")
    with open(config_file, "w") as f:
        lines = ["SEC_PASSWORD_FILE = {}\n".format(password_file),
                 "SEC_CLIENT_AUTHENTICATION_METHODS = PASSWORD\n",
                 "SCHEDD_HOST = {}\n".format(schedd_host),
                 "CONDOR_HOST = {}\n".format(condor_host)]
        f.writelines(lines)

if not os.path.isfile(password_file):
    logging.info("About to write password file")
    import subprocess

    subprocess.check_output(
        "{} -p '{}' -f {}".format(password_binary, password, password_file), shell=True)
