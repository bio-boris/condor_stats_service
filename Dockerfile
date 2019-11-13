FROM kbase/sdkbase2:python
MAINTAINER KBase Developer
# -----------------------------------------
# In this section, you can install any system dependencies required
# to run your App.  For instance, you could place an apt-get update or
# install line here, a git checkout to download code, or run any other
# installation scripts.

RUN apt-get update && apt-get install -y vim wget \
&& wget -qO - https://research.cs.wisc.edu/htcondor/debian/HTCondor-Release.gpg.key | sudo apt-key add - \
&& echo "deb http://research.cs.wisc.edu/htcondor/debian/8.8/stretch stretch contrib" >> /etc/apt/sources.list \
&& apt-get update && export DEBIAN_FRONTEND=noninteractive && apt-get install -y condor && rm -rf /etc/condor/*

RUN sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 4B7C549A058F8B6B && echo "deb http://repo.mongodb.org/apt/debian "$(lsb_release -sc)"/mongodb-org/4.2 main" | sudo tee /etc/apt/sources.list.d/mongodb.list && apt update -y && apt install -y mongodb-org 

RUN mkdir -p /data/db && pip install htcondor pymongo


# -----------------------------------------

COPY ./ /kb/module
RUN mkdir -p /kb/module/work
RUN chmod -R a+rw /kb/module

WORKDIR /kb/module

RUN make all

ENTRYPOINT [ "./scripts/entrypoint.sh" ]

CMD [ ]
