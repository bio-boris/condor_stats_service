/*
A KBase module: condor_stats
*/

module condor_stats {
    typedef structure {
        string report_name;
        string report_ref;
    } ReportResults;

    funcdef queue_status(mapping<string,string> params) returns (ReportResults output) authentication required;
    funcdef job_status(mapping<string,string> params) returns (ReportResults output) authentication required;
};
