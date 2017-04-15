#!/bin/bash
pip2 install virtualenv
virtualenv venv
source venv/bin/activate
pip2 install -r requirements.txt
command -v zip >/dev/null 2>&1 || { echo "Zip is not installed or not accessible. Please install Zip. Aborting" >&2; exit 1; }
command -v fastq-dump >/dev/null 2>&1 || { echo "fastq-dump is not installed or not accessible. Please install fastq-dump. Aborting" >&2; exit 1; }
command -v fastqc >/dev/null 2>&1 || { echo "fastqc is not installed or not accessible. Please install fastqc. Aborting" >&2; exit 1; }
command -v hisat2 >/dev/null 2>&1 || { echo "hisat2 is not installed or not accessible. Please install hisat2. Aborting" >&2; exit 1; }
command -v cufflinks >/dev/null 2>&1 || { echo "cufflinks is not installed or not accessible. Please install cufflinks. Aborting" >&2; exit 1; }
command -v cuffquant >/dev/null 2>&1 || { echo "cuffquant is not installed or not accessible. Please install cuffquant. Aborting" >&2; exit 1; }
command -v cuffnorm >/dev/null 2>&1 || { echo "cuffnorm is not installed or not accessible. Please install cuffnrom. Aborting" >&2; exit 1; }
command -v samtools >/dev/null 2>&1 || { echo "samtools is not installed or not accessible. Please install samtools. Aborting" >&2; exit 1; }

mongo --eval "db.stats()"  

RESULT=$?   

if [ $RESULT -ne 0 ]; then
    echo "mongodb not running on this server"

cp config_example.yaml config.yaml
    