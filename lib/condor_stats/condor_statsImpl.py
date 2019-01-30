# -*- coding: utf-8 -*-
#BEGIN_HEADER
import logging
import os

from installed_clients.KBaseReportClient import KBaseReport
from .condor_utils import get_queue_stats,get_jobs_status,connect
#END_HEADER


class condor_stats:
    '''
    Module Name:
    condor_stats

    Module Description:
    A KBase module: condor_stats
    '''

    ######## WARNING FOR GEVENT USERS ####### noqa
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    ######################################### noqa
    VERSION = "0.0.1"
    GIT_URL = "https://bio-boris@github.com/bio-boris/condor_stats_service.git"
    GIT_COMMIT_HASH = "a4d8d48175bee58c111b744d87f5e3491c743f57"

    #BEGIN_CLASS_HEADER
    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.shared_folder = config['scratch']
        self.serviceWizardURL = config['srv-wiz-url']
        logging.basicConfig(format='%(created)s %(levelname)s: %(message)s',
                            level=logging.INFO)
        #END_CONSTRUCTOR
        pass


    def queue_status(self, ctx, params):
        """
        :param params: instance of mapping from String to String
        :returns: instance of mapping from String to String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN queue_status
        #output = get_queue_stats()

        connect()
        output = {}

        #END queue_status

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method queue_status return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]

    def job_status(self, ctx, params):
        """
        :param params: instance of mapping from String to String
        :returns: instance of mapping from String to String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN job_status
        #output = get_jobs_status(None)
        output = {}
        #END job_status

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method job_status return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]
    def status(self, ctx):
        #BEGIN_STATUS
        returnVal = {'state': "OK",
                     'message': "",
                     'version': self.VERSION,
                     'git_url': self.GIT_URL,
                     'git_commit_hash': self.GIT_COMMIT_HASH}
        #END_STATUS
        return [returnVal]
