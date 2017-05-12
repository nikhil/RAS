#!/bin/bash
RED='\033[0;31m'
Blue='\033[0;34m'
Light_blue='\033[1;34m' 
Purple='\033[0;35m'
Yellow='\033[0;33m'
NoColor='\033[0m'
command -v python2 >/dev/null 2>&1 || {  echo -e "${RED}Error:${NoColor} python2 is not installed or not accessible. Please install python2. Aborting" >&2; exit 1; }
echo -e "${Light_blue}Passed:${NoColor} python2 is installed"
command -v R >/dev/null 2>&1 || {  echo -e "${RED}Error:${NoColor} R is not installed or not accessible. Please install R. Aborting" >&2; exit 1; }
echo -e "${Light_blue}Passed:${NoColor} R is installed"
command -v pip2 >/dev/null 2>&1 || {  echo -e "${RED}Error:${NoColor} pip2 is not installed or not accessible. Please install pip2. Aborting" >&2; exit 1; }
echo -e "${Light_blue}Passed:${NoColor} pip2 is installed"
command -v virtualenv >/dev/null 2>&1 || {  echo -e "${RED}Error:${NoColor} virtualenv is not installed or not accessible. Please install virtualenv. ${Purple}'sudo pip install virtualenv'${NoColor} Aborting" >&2; exit 1; }
echo -e "${Light_blue}Passed:${NoColor} virtualenv is installed"
virtualenv venv
source venv/bin/activate
echo "Installing python packages"
pip2 install -r requirements.txt
mkdir /usr/local/lib/R/site-library/test >/dev/null 2>&1
if [ $? -ne 0 ]; then
	echo -e "${RED}Error:${NoColor} R local library /usr/local/lib/R/site-library/ is not writable. Please run ${Purple}'sudo chmod o+w /usr/local/lib/R/site-library/'${NoColor} .Aborting" 
	exit 1;
else
	rm -r /usr/local/lib/R/site-library/test
fi
echo "Installing R packages"
Rscript $PWD/RScripts/install_packages.r
command -v screen >/dev/null 2>&1 || { echo -e "${RED}Error:${NoColor} screen is not installed or not accessible. Please install screen. Aborting" >&2; exit 1; }
echo -e "${Light_blue}Passed:${NoColor} screen is installed"
command -v zip >/dev/null 2>&1 || { echo -e "${RED}Error:${NoColor} zip is not installed or not accessible. Please install zip. Aborting" >&2; exit 1; }
echo -e "${Light_blue}Passed:${NoColor} Zip is installed"
command -v fastq-dump >/dev/null 2>&1 || {  echo -e "${RED}Error:${NoColor} fastq-dump is not installed or not accessible. Please install fastq-dump. Aborting" >&2; exit 1; }
echo -e "${Light_blue}Passed:${NoColor} fastq-dump is installed"
command -v fastqc >/dev/null 2>&1 || { echo -e "${RED}Error:${NoColor} fastqc is not installed or not accessible. Please install fastqc. Aborting" >&2; exit 1; }
echo -e "${Light_blue}Passed:${NoColor} fastqc is installed"
command -v hisat2 >/dev/null 2>&1 || { echo -e "${RED}Error:${NoColor} hisat2 is not installed or not accessible. Please install hisat2. Aborting" >&2; exit 1; }
echo -e "${Light_blue}Passed:${NoColor} hisat2 is installed"
command -v cufflinks >/dev/null 2>&1 || { echo -e "${RED}Error:${NoColor} cufflinks is not installed or not accessible. Please install cufflinks. Aborting" >&2; exit 1; }
echo -e "${Light_blue}Passed:${NoColor} cufflinks is installed"
command -v cuffquant >/dev/null 2>&1 || { echo -e "${RED}Error:${NoColor} cuffquant is not installed or not accessible. Please install cuffquant. Aborting" >&2; exit 1; }
echo -e "${Light_blue}Passed:${NoColor} cuffquant is installed"
command -v cuffnorm >/dev/null 2>&1 || { echo -e "${RED}Error:${NoColor} cuffnorm is not installed or not accessible. Please install cuffnorm. Aborting" >&2; exit 1; }
echo -e "${Light_blue}Passed:${NoColor} cuffnorm is installed"
command -v samtools >/dev/null 2>&1 || { echo -e "${RED}Error:${NoColor} samtools is not installed or not accessible. Please install samtools. Aborting" >&2; exit 1; }
echo -e "${Light_blue}Passed:${NoColor} samtools is installed"
mongo_status=$(pgrep mongod)
if [ -z "$mongo_status" ]; then
	echo -e "${Yellow}Warning:${NoColor} MongoDB is not running on this server"
else
	echo -e "${Light_blue}Passed:${NoColor} MongoDB is running on this server"

fi
if [ ! -f config.yaml ]; then
   cp config_example.yaml config.yaml
   echo -e "${Blue}Note:${NoColor} Configuration file generated. Make sure to edit ${Purple}'config.yaml'${NoColor}." 
fi  