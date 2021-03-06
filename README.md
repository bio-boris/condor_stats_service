# condor_stats

This is a [KBase](https://kbase.us) module generated by the [KBase Software Development Kit (SDK)](https://github.com/kbase/kb_sdk).

You will need to have the SDK installed to use this module. [Learn more about the SDK and how to use it](https://kbase.github.io/kb_sdk_docs/).

You can also learn more about the apps implemented in this module from its [catalog page](https://narrative.kbase.us/#catalog/modules/condor_stats) or its [spec file]($module_name.spec).

# Setup and test

Add your KBase developer token to `test_local/test.cfg` and run the following:

```bash
$ make
$ kb-sdk test
```

After making any additional changes to this repo, run `kb-sdk test` again to verify that everything still works.

# Installation from another module

To use this code in another SDK module, call `kb-sdk install condor_stats` in the other module's root directory.

# Help

You may find the answers to your questions in our [FAQ](https://kbase.github.io/kb_sdk_docs/references/questions_and_answers.html) or [Troubleshooting Guide](https://kbase.github.io/kb_sdk_docs/references/troubleshooting.html).


# Architecture

* Dynamic service has a mongodb store to keep a few records. Records are expired after 600 seconds (configurable with RECORD_EXPIRY_TIME_SECONDS) and deleted.
* Dynamic service has env variables ['COLLECTOR_HOST','CONDOR_HOST','POOL_PASSWORD','SCHEDD_HOST'] in order to run run condor_q, condor_status and condor_userprio on the condor hosts.
* Two sets of ENV variables are required for appdev/prod
* Upon startup, dynamic service runs "Generate_data_dump" to dump condor_q data into service.
* A cronjob runs to generate fresh data every 5 minutes (configurable with CRONJOB_RUN_FREQUENCY_SECONDS)

# Testing

```
docker build . -t test/condor_stats:latest; docker run -p 5000:5000 -e AUTH_SERVICE_URL=https://ci.kbase.us/services/auth/api/legacy/KBase/Sessions/Login -e KBASE_ENDPOINT=https://ci.kbase.us/services -e KBASE_SECURE_CONFIG_PARAM_POOL_PASSWORD_CI="" test/condor_stats:latest
```

The config should look like

```
[condor_stats]
kbase-endpoint = https://ci.kbase.us/services
job-service-url = https://ci.kbase.us/services/userandjobstate
workspace-url = https://ci.kbase.us/services/ws
shock-url = https://ci.kbase.us/services/shock-api
handle-service-url = https://ci.kbase.us/services/handle_service
srv-wiz-url = https://ci.kbase.us/services/service_wizard
njsw-url = https://ci.kbase.us/services/njs_wrapper
auth-service-url = https://ci.kbase.us/services/auth/api/legacy/KBase/Sessions/Login
auth-service-url-allow-insecure = false
scratch = /kb/module/work/tmp
```