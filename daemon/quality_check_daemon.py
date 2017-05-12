from daemon import Daemon
import sys
import time
import os
from pymongo import MongoClient
from bs4 import BeautifulSoup
import sendgrid
from sendgrid.helpers.mail import *
import shutil
import requests
import zipfile
import ftplib
import subprocess
import filelock
import yaml

project_dir = os.getcwd()[:-7]
web_mutex = filelock.FileLock(project_dir+"/GEO_access.lock")

class quality_check(Daemon):

		
	def run(self):
		with open(os.path.join(os.pardir, "config.yaml")) as config:
			config_map = yaml.safe_load(config)
		ip = config_map['ip']
		sendgrid_api_key = config_map['sendgrid_api_key']
		mongo_url = config_map['mongo_url']
		email_address = config_map['email_address']

		
		def send_email(email_to,email_from,email_subject,email_body):
			if sendgrid_api_key != '':
				sg_client = sendgrid.SendGridAPIClient(apikey=sendgrid_api_key)
				to_email = Email(email_to)
				from_email = Email(email_from)
				content = Content('text/html',email_body)
				mail = Mail(from_email, email_subject, to_email, content)
				response = sg_client.client.mail.send.post(request_body=mail.get())

		def quality_check(input_file):
			quality_file = open(input_file)
			on_table = 0
			on_duplication = 0
			total_bases = 0
			total_score = 0
			for single_line in quality_file:
				if single_line == '>>END_MODULE\n':
					on_table = 0
					on_duplication = 0
				if single_line == '#Base	Mean	Median	Lower Quartile	Upper Quartile	10th Percentile	90th Percentile\n':
					on_table = 1
				elif '>>Sequence Duplication Levels' in single_line:
					on_duplication = 1
				else:
					if on_table != 1 and on_duplication != 1:
						continue
					if on_table == 1:
						trimmed_single_line = single_line[:-1]
						line_contents = trimmed_single_line.split("\t")
						base_numbers = line_contents[0].split("-")
						if len(base_numbers) == 1:
							total_score = total_score + float(line_contents[1])
							total_bases = total_bases + 1
						else:
							base_width = float(base_numbers[1]) - float(base_numbers[0]) + 1
							total_score = total_score +  base_width* float(line_contents[1])
							total_bases = total_bases + base_width
					if on_duplication == 1:
						percentage_line_list = single_line.split(" ")
						further_splitting = percentage_line_list[-1].split('\t')
						percentage_num =  float(further_splitting[-1])
						on_duplication = 0
						
			return {'avg_base_score':((total_score/float(total_bases))/float(40))*100,'deduplication':percentage_num}

		def unzip_and_analyze(file_name):
			abs_path = os.path.abspath(file_name)
			zip_ref = zipfile.ZipFile(abs_path)
			zip_ref.extractall(os.getcwd())
			zip_ref.close()
			#os.remove(abs_path)

		def analyze_compressed_file(file_name,GEO_Num,sample_name,keep_files,user_name,user_email):
			fastq_dump_call = subprocess.call(['fastq-dump',file_name])
			print "Conversion Finished"
			fastq_file_name = file_name[:-4] + '.fastq'
			print "Quality check on Fastq:"
			fastqc_call = subprocess.call(['fastqc',fastq_file_name])
			print "Decompressing Results:"
			fastqc_zip_name  = file_name[:-4] + '_fastqc.zip'
			unzip_and_analyze(fastqc_zip_name)
			print "Retrieving Results:"
			fastqc_results_filename =  file_name[:-4] + '_fastqc/fastqc_data.txt'
			results = quality_check(fastqc_results_filename)
			quality_check_file = GEO_Num  + '_Quality_Check.xls'
			if not os.path.isfile(quality_check_file):
				with open(quality_check_file,'w') as quality_check_pointer:
					quality_check_pointer.write('Sample Number\tSample Name\tAvereage Base Score\tDeduplication Percentage\n')
					quality_check_pointer.write(file_name[:-4]+'\t' + sample_name + '\t' + str(results['avg_base_score']) + '\t' + str(results['deduplication'])+'\n')
			else:
				with open(quality_check_file,'a') as quality_check_pointer:
					quality_check_pointer.write(file_name[:-4]+'\t' + sample_name + '\t' + str(results['avg_base_score']) + '\t' + str(results['deduplication'])+'\n')
			if keep_files == 0:
				print "removing excess files:"
				os.remove(file_name)
				os.remove(fastq_file_name)
				os.remove(fastqc_zip_name)
				qc_folder_name = file_name[:-4] + '_fastqc'
				html_file = qc_folder_name + '.html'
				shutil.rmtree(qc_folder_name)
				os.remove(html_file)	


		def ftp_connect(url):
			ftp = ftplib.FTP(url)
			logged_in = False
			error_count = 0
			while logged_in == False:
				try:
					ftp.login()
					logged_in = True
				except ftplib.error_perm as ftp_error:
					if error_count < 3:
						print 'Got error '+str(ftp_error)
						error_count = error_count + 1
						time.sleep(5)
					else:
						raise ftp_error
			return ftp


		def parse_html(GEO_Num,keep_files,user_name,user_email):
			html_file = requests.get('https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=' + str(GEO_Num)).text
			soup = BeautifulSoup(html_file, 'html.parser')
			link_list = []
			sample_name = ''
			for single_link in soup.find_all('a'):
				if 'geo/query/acc.cgi?acc=' in single_link.get('href') and 'GSM' in single_link.get('href'):
					link_list.append(single_link.get('href'))			
			#for sample_link in link_list:
			for sample_link in link_list:
				sample_html = requests.get('https://www.ncbi.nlm.nih.gov'+sample_link).text
				second_soup = BeautifulSoup(sample_html,'html.parser')
				name_list = second_soup.find_all('td')
				found_title = 0
				for td_elem in name_list:
					if found_title == 0:
						if td_elem.text == 'Title':
							found_title = 1
					else:
						if found_title == 1:
							sample_name = td_elem.text
							break
				second_link_list = second_soup.find_all('a')
				for single_link in  second_link_list:
					if 'ftp://ftp-trace' in single_link.get('href'):
						ftp = ftp_connect(single_link.get('href')[6:32])
						#ftplib.error_perm: 530 Sorry, max 700 users -- try again later
						ftp.cwd(single_link.get('href')[33::])
						folder_names = ftp.nlst()
						parent_directory = ftp.pwd()
						for folder_name in folder_names:
							try:
								ftp.cwd('{}/{}'.format(parent_directory,folder_name))
								file_names = ftp.nlst()
							except Exception as e:
								print 'Got error ' + str(e)
								ftp = ftp_connect(single_link.get('href')[6:32])
								ftp.cwd('{}/{}'.format(parent_directory,folder_name))
								file_names = ftp.nlst()

							for file_name in file_names:
								with open(file_name,'w') as file_pointer:							
									print "Downloading: " + file_name
									web_mutex.acquire()
									try:
										ftp.retrbinary('RETR '+file_name,file_pointer.write)
									except Exception as e:
										ftp = ftp_connect(single_link.get('href')[6:32])
										ftp.cwd('{}/{}'.format(parent_directory,folder_name))
										ftp.retrbinary('RETR '+file_name,file_pointer.write)
									finally:
										web_mutex.release()
									print "Download Finished"
								print "Converting to fastq: "
								analyze_compressed_file(file_name,GEO_Num,sample_name,keep_files,user_name,user_email)
								time.sleep(1.5)
		while True:
			client = MongoClient(mongo_url)			
			experiment_db = client.experiment_database
			quality_collection =experiment_db.quality_collection
			quality_queue = quality_collection.find_one({'name':'experiment_queue'})			
			if quality_queue != None:
				dict_queue = quality_queue['data']
				if len(dict_queue) >0:
					quality_control_dict = dict_queue.pop(0)			
					geo_number = quality_control_dict['geo_number']
					user_name = quality_control_dict['user_name']
					user_email = quality_control_dict['user_email']
					quality_queue['data'] = dict_queue
					quality_collection.replace_one({'name':'experiment_queue'},quality_queue)
					output_folder = project_dir+'/static/data/quality_check/'+str(geo_number)+'/'
					if os.path.isdir(output_folder):
						shutil.rmtree(output_folder)
					os.makedirs(output_folder)
					os.chdir(output_folder)
					parse_html(geo_number,0,user_name,user_email)
					output_file = geo_number + '_Quality_Check.xls'
					output_link = ip+'/static/data/quality_check/'+str(geo_number)+'/'+str(output_file)				
					email_body = 'Dear '+ user_name+'<br> Your quality check analysis for '+str(geo_number)+'has been finished. You can download the result here:'+output_link+'<br>Sincerely,<br>RAS Notifier'
					send_email(user_email,email_address,'Finished Quality Check Analysis for GEO number: '+str(geo_number),email_body)				
			time.sleep(300)
		



if __name__ == "__main__":
	daemon = quality_check(os.getcwd()+'/quality_check.pid',stdin='/dev/null', stdout=os.getcwd()+'/quality_check.log', stderr=os.getcwd()+'/quality_check_err.log')
	if len(sys.argv) == 2:
		if 'start' == sys.argv[1]:
			daemon.start()
		elif 'stop' == sys.argv[1]:
			daemon.stop()
		elif 'restart' == sys.argv[1]:
			daemon.restart()
		else:
			print "Unknown command"
			sys.exit(2)
		sys.exit(0)
	else:
		print "usage: %s start|stop|restart" % sys.argv[0]
		sys.exit(2)