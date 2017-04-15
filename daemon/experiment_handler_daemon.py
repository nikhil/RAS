from daemon import Daemon
import sys
import time
import os
from pymongo import MongoClient
import sendgrid
from sendgrid.helpers.mail import *
import re
import subprocess
import shutil
import json
import multiprocessing.dummy as threads
import yaml

project_dir = os.getcwd()[:-7]

class experiment_handler(Daemon):

		
	def run(self):
		with open(os.path.join(os.pardir, "config.yaml")) as config:
			config_map = yaml.safe_load(config)
		sendgrid_api_key = config_map['sendgrid_api_key']
		genome_files = config_map['genome_files']
		num_threads = config_map['num_threads']
		mongo_url = config_map['mongo_url']
		email_address = config_map['email_address']
		ip = config_map['ip']
		top_hat_threads = str(config_map['top_hat_threads'])
		no_covereage_search = ''
		if config_map['no-coverage-search'] == True:
			no_covereage_search = '--no-coverage-search'


		def sequence_worker(sequence_tuple):
			sample_1_fastq_file = sequence_tuple[0]
			sample_2_fastq_file = sequence_tuple[1]
			directory = sequence_tuple[2]
			gtf = sequence_tuple[3]
			genome = sequence_tuple[4]
			analysis_type = sequence_tuple[5]
			library_type = sequence_tuple[6]
			
			#os.chdir(directory)
			thout_folder = directory+'/thout'
			qout_folder = directory+'/qout'
			lout_folder = directory+'/lout'			
			if sample_2_fastq_file != None:
				#tophat2 -o thout1_firststrand -p 8 --library-type=fr-firststrand -G ~/Mouse_data/Mus_musculus/UCSC/mm10/Annotation/genes.gtf ~/Mouse_data/Mus_musculus/UCSC/mm10/Sequence/Bowtie2Index/genome sample1_1.fastq sample1_2.fastq
				sample_1_fastq = directory+'/'+sample_1_fastq_file
				sample_2_fastq = directory+'/'+sample_2_fastq_file
				subprocess.call(['tophat2','-o',thout_folder,'-p',top_hat_threads,no_covereage_search,'--library-type',library_type,'-G',gtf,genome,sample_1_fastq,sample_2_fastq])				
				os.remove(sample_1_fastq)
				os.remove(sample_2_fastq)
			else:
				sample_1_fastq = directory+'/'+sample_1_fastq_file
				subprocess.call(['tophat2','-o',thout_folder,'-p',top_hat_threads,no_covereage_search,'--library-type',library_type,'-G',gtf,genome,sample_1_fastq])
				os.remove(sample_1_fastq)
			for single_file in os.listdir(directory):
				if '.sra' in single_file:
					sra_path = directory + '/'+single_file
					#os.remove(sra_path)
			#cuffquant--------------------------
			bam_file = directory+'/thout/accepted_hits.bam'
			#cuffquant -o CELL_T24_A01_cuffquant_out GENCODE.gtf CELL_T24_A01_thout/accepted_hits.bam
			if analysis_type == 1:
				subprocess.call(['cuffquant','-o',qout_folder,'-p',top_hat_threads,'-q','--library-type',library_type,gtf,bam_file])
			else:
				subprocess.call(['cufflinks','-o',qout_folder,'-p',top_hat_threads,'-q','--library-type',library_type,gtf,bam_file])





		def send_email(email_to,email_from,email_subject,email_body):
			if sendgrid_api_key != '':
				sg_client = sendgrid.SendGridAPIClient(apikey=sendgrid_api_key)
				to_email = Email(email_to)
				from_email = Email(email_from)
				content = Content('text/html',email_body)
				mail = Mail(from_email, email_subject, to_email, content)
				response = sg_client.client.mail.send.post(request_body=mail.get())
		def get_sample_and_condition_num(path_str):
			condition_folder = (re.search('condition_\d+',path_str)).group()
			sample_folder = (re.search('sample_\d+',path_str)).group()
			condition_num = (re.search('\d+',condition_folder)).group()
			sample_num = (re.search('\d+',sample_folder)).group()
			return {'sample_num':sample_num,'condition_num':condition_num}

		while True:
			client = MongoClient(mongo_url)
			experiment_db = client.experiment_database
			norm_collection =experiment_db.normalize_collection
			diff_collection = experiment_db.diff_collection
			experiment_queue = norm_collection.find_one({'name':'experiment_queue'})
			experiment_queue1 = diff_collection.find_one({'name':'experiment_queue'})
			if experiment_queue != None:
				queue = experiment_queue['data']
				if len(queue) > 0:					
					experiment_id = queue.pop(0)
					experiment_queue['data'] = queue
					norm_collection.replace_one({'name':'experiment_queue'},experiment_queue)
					#original_directory_dict = norm_collection.find_one({'name':'original_directory'})
					#original_directory = original_directory_dict['data']
					original_directory = project_dir
					#server_ip_dict = norm_collection.find_one({'name':'server_ip'})
					#server_ip = server_ip_dict['data']
					server_ip = ip
					folder_path = original_directory+'/data/normalize/'+str(experiment_id)
					os.chdir(folder_path)
					#quality check-----------------------------------
					quality_check_email_body = ""
					html_destination_folder = original_directory+'/static/data/normalize/'+str(experiment_id)+'/'
					
					if os.path.isdir(html_destination_folder):
						shutil.rmtree(html_destination_folder)
					os.makedirs(html_destination_folder)
					for subdir, dirs, files in os.walk(folder_path):
						for single_file in files:
							if '.sra' in single_file:
								os.chdir(subdir)
								#fastq-dump --split-files SRR1971738.sra
								subprocess.call(['fastq-dump','--split-files',single_file])
								#fastqc SRR1971738_1.fastq
								fastq_file = single_file[:-4]+'_1.fastq'
								subprocess.call(['fastqc',fastq_file])
								html_source_file = subdir+'/'+ single_file[:-4]+'_1_fastqc.html'								
								shutil.copy(html_source_file,html_destination_folder)
								sample_information = get_sample_and_condition_num(subdir)
								quality_check_email_body = quality_check_email_body + '<li>'+single_file[:-4]+' ( Condition: '+sample_information['condition_num']+' Sample: '+sample_information['sample_num']+' ) <br>'+server_ip+'/static/data/normalize/'+str(experiment_id)+'/'+single_file[:-4]+'_1_fastqc.html</li>'
					
					with open(folder_path+'/user_info.json') as user_info_data:
						user_data = json.load(user_info_data)
					with open(folder_path+'/condition_names.json') as condition_names_data:
						condition_names = json.load(condition_names_data)
					with open(folder_path+'/sample_sheet.txt','w') as sample_sheet_input:
						sample_sheet_input.write('sample_id\tgroup_label\n')						
					with open(folder_path+'/experiment_info.json') as experiment_info:
						experiment_data = json.load(experiment_info)

					library_type = experiment_data['library_type']
					genome_name = experiment_data['genome']
					genome_location = ''
					genome_gtf_location = ''

					for single_genome in genome_files:
						if single_genome['name'] == genome_name:
							genome_location = single_genome['genome']
							genome_gtf_location = single_genome['gtf']
										
					quality_check_email_body = 'Dear '+user_data['user_name']+'<br>Your sequence files have been processed through quality check. You can check the results of each sample by clicking on the corresponding links below.<br><ul>'+quality_check_email_body+'</ul><br>Sincerely,<br>RAS Notifier'
					send_email(user_data['user_email'],email_address,'Normalized Experiment Quality Check ID: '+str(experiment_id),quality_check_email_body)
					
					#alignment-----------------------------
					process_pool = threads.Pool(num_threads)
					condition_folders = os.walk(folder_path).next()[1]
					sequence_job_list = []					
					for single_condition_folder in condition_folders:
						full_condition_path = folder_path+'/'+single_condition_folder
						for sample_subdir, sample_dirs, sample_files in os.walk(full_condition_path):							
							sample_1_fastq = None
							sample_2_fastq = None
							for single_sample_file in sample_files:
								if '_1.fastq' in single_sample_file:
									sample_1_fastq = single_sample_file
								elif '_2.fastq' in single_sample_file:
									sample_2_fastq = single_sample_file
							if sample_1_fastq != None:
								sequence_job_list.append((sample_1_fastq,sample_2_fastq,sample_subdir,genome_gtf_location,genome_location,1,library_type))
								condition_num = (re.search('\d+',single_condition_folder)).group()
								group_label = condition_names[str(condition_num)]
								sample_id = sample_subdir +'/qout/abundances.cxb'
								with open(folder_path+'/sample_sheet.txt','a') as sample_sheet_input:
									sample_sheet_input.write(str(sample_id+'\t'+group_label+'\n'))
					try:
						process_pool.map(sequence_worker,sequence_job_list)
					except:
						process_pool.terminate()
						process_pool.join()
						raise
					process_pool.close()
					process_pool.join()
										
					os.chdir(folder_path)
					
					sample_sheet_path = folder_path+'/sample_sheet.txt'
					subprocess.call(['cuffnorm','-o','cnout','-q','-p',top_hat_threads,'--library-type',library_type,'--use-sample-sheet',genome_gtf_location,sample_sheet_path])
					
					output_name = str(experiment_id)+'.zip'
					cuffnorm_folder = 'cnout/' 
					subprocess.call(['zip','-r',output_name,cuffnorm_folder])
					compressed_output = folder_path+'/'+output_name
					shutil.copy(compressed_output,html_destination_folder)
					url_link = server_ip+'/static/data/normalize/'+str(experiment_id)+'/'+output_name


					finished_email_body = 'Dear '+user_data['user_name']+'<br>We finished processing your sequence files. You can access the output here: <br>'+ url_link+'<br>Sincerely,<br>RAS Notifier'
					send_email(user_data['user_email'],email_address,'Normalized Experiment Finished ID: '+str(experiment_id),finished_email_body)
					norm_collection =experiment_db.normalize_collection
			if experiment_queue1 != None:
				queue1 = experiment_queue1['data']
				if len(queue1) > 0:					
					experiment_id = queue1.pop(0)
					experiment_queue1['data'] = queue1
					diff_collection.replace_one({'name':'experiment_queue'},experiment_queue1)
					original_directory_dict = norm_collection.find_one({'name':'original_directory'})
					original_directory = original_directory_dict['data']
					server_ip_dict = norm_collection.find_one({'name':'server_ip'})
					server_ip = server_ip_dict['data']
					folder_path = original_directory+'/data/diff/'+str(experiment_id)
					os.chdir(folder_path)
					#quality check-----------------------------------
					quality_check_email_body = ""
					html_destination_folder = original_directory+'/static/data/diff/'+str(experiment_id)+'/'
					if os.path.isdir(html_destination_folder):
						shutil.rmtree(html_destination_folder)
					os.makedirs(html_destination_folder)
					for subdir, dirs, files in os.walk(folder_path):
						for single_file in files:
							if '.sra' in single_file:
								os.chdir(subdir)
								#fastq-dump --split-files SRR1971738.sra
								subprocess.call(['fastq-dump','--split-files',single_file])
								#fastqc SRR1971738_1.fastq
								fastq_file = single_file[:-4]+'_1.fastq'
								subprocess.call(['fastqc',fastq_file])
								html_source_file = subdir+'/'+ single_file[:-4]+'_1_fastqc.html'								
								shutil.copy(html_source_file,html_destination_folder)
								sample_information = get_sample_and_condition_num(subdir)
								quality_check_email_body = quality_check_email_body + '<li>'+single_file[:-4]+' ( Condition: '+sample_information['condition_num']+' Sample: '+sample_information['sample_num']+' ) <br>'+server_ip+'/static/data/diff/'+str(experiment_id)+'/'+single_file[:-4]+'_1_fastqc.html</li>'
					
					with open(folder_path+'/user_info.json') as user_info_data:
						user_data = json.load(user_info_data)
					with open(folder_path+'/condition_names.json') as condition_names_data:
						condition_names = json.load(condition_names_data)
					with open(folder_path+'/sample_sheet.txt','w') as sample_sheet_input:
						sample_sheet_input.write('sample_id\tgroup_label\n')
					with open(folder_path+'/experiment_info.json') as experiment_info:
						experiment_data = json.load(experiment_info)

					library_type = experiment_data['library_type']
					genome_name = experiment_data['genome']
					genome_location = ''
					genome_gtf_location = ''

					for single_genome in genome_files:
						if single_genome['name'] == genome_name:
							genome_location = single_genome['genome']
							genome_gtf_location = single_genome['gtf']

					
					quality_check_email_body = 'Dear '+user_data['user_name']+'<br>Your sequence files have been processed through quality check. You can check the results of each sample by clicking on the corresponding links below.<br><ul>'+quality_check_email_body+'</ul><br>Sincerely,<br>RAS Notifier'
					send_email(user_data['user_email'],email_address,'Differential Experiment Quality Check ID: '+str(experiment_id),quality_check_email_body)
					
					#alignment-----------------------------
					process_pool = threads.Pool(num_threads)
					condition_folders = os.walk(folder_path).next()[1]
					sequence_job_list = []					
					for single_condition_folder in condition_folders:
						full_condition_path = folder_path+'/'+single_condition_folder
						for sample_subdir, sample_dirs, sample_files in os.walk(full_condition_path):							
							sample_1_fastq = None
							sample_2_fastq = None
							for single_sample_file in sample_files:
								if '_1.fastq' in single_sample_file:
									sample_1_fastq = single_sample_file
								elif '_2.fastq' in single_sample_file:
									sample_2_fastq = single_sample_file
							if sample_1_fastq != None:
								sequence_job_list.append((sample_1_fastq,sample_2_fastq,sample_subdir,genome_gtf_location,genome_location,2,library_type))
								condition_num = (re.search('\d+',single_condition_folder)).group()
								group_label = condition_names[str(condition_num)]
								sample_id = sample_subdir +'/thout/accepted_hits.bam'
								sample_gtf = sample_subdir+'/lout/transcripts.gtf'
								with open(folder_path+'/sample_sheet.txt','a') as sample_sheet_input:
									sample_sheet_input.write(str(sample_id+'\t'+group_label+'\n'))
								with open(folder_path+'/assemblies.txt','a') as assemblies_input:
									assemblies_input.write(str(sample_gtf))
					try:
						process_pool.map(sequence_worker,sequence_job_list)
					except:
						process_pool.terminate()
						process_pool.join()
					process_pool.close()
					process_pool.join()
					os.chdir(folder_path)
					sample_sheet_path = folder_path+'/sample_sheet.txt'
					subprocess.call(['cuffmerge','-g',genome_gtf_location,'-s',genome_location,'-p',top_hat_threads,'assemblies.txt'])
					subprocess.call(['cuffdiff','-o','cdout','-q','-p',top_hat_threads,'--library-type',library_type,'--use-sample-sheet',genome_gtf_location,sample_sheet_path])
					output_name = str(experiment_id)+'.zip'
					cuffdiff_folder = 'cdout/' 
					subprocess.call(['zip','-r',output_name,cuffdiff_folder])
					compressed_output = folder_path+'/'+output_name
					shutil.copy(compressed_output,html_destination_folder)
					url_link = server_ip+'/static/data/diff/'+str(experiment_id)+'/'+output_name


					finished_email_body = 'Dear '+user_data['user_name']+'<br>We finished processing your sequence files. You can access the output here: <br>'+ url_link+'<br>Sincerely,<br>RnaSeqAnalysisSuite Notifier'
					send_email(user_data['user_email'],'RnaSeqAnalysisSuite@rutgers.edu','Differential Experiment Finished ID: '+str(experiment_id),finished_email_body)

			time.sleep(60)


if __name__ == "__main__":
	daemon = experiment_handler(os.getcwd()+'/experiment_handler.pid',stdin='/dev/null', stdout=os.getcwd()+'/experiment_handler_out.log', stderr=os.getcwd()+'/experiment_handler_err.log')
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