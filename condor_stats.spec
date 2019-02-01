/*
A KBase module: condor_stats
*/

module condor_stats {
    typedef structure {
        string report_name;
        string report_ref;
    } ReportResults;

    typedef structure {
        string id;
    } job;

    funcdef queue_status(mapping<string,string> params) returns (mapping<string,string> output) authentication required;
    funcdef job_status(mapping<string,string> params) returns (mapping<string,string> output) authentication required;
    funcdef condor_userprio_all(mapping<string,string> params) returns (mapping<string,string> output) authentication required;
};
