#!/usr/bin/env python

import logging
import os

# TODO USE ENV VARIABLES


logging.info("About to setup condor")
condor_config_dir = "/etc/condor"
os.makedirs(condor_config_dir, exist_ok=True)

config_file = "{}/condor_config".format(condor_config_dir)
password_file = "{}/password".format(condor_config_dir)
password_binary = "/usr/sbin/condor_store_cred"

schedd_host = os.environ.get("KBASE_SECURE_CONFIG_PARAM_SCHEDD_HOST", "kbase@ci-dock")
condor_host = os.environ.get("KBASE_SECURE_CONFIG_PARAM_CONDOR_HOST", "ci.kbase.us:9618")
password = os.environ.get("KBASE_SECURE_CONFIG_PARAM_POOL_PASSWORD", "weakpassword")


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
