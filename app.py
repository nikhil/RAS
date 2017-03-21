import os
import sys
from flask import Flask, request, flash, url_for, redirect, \
     render_template, abort, send_from_directory
from werkzeug import secure_filename
from random import randint
import operator
import requests
import zipfile
import shutil
import json
import subprocess
import time
from pymongo import MongoClient
import sendgrid
from sendgrid.helpers.mail import *
import randomcolor
from threading import Thread, Lock, Event
from bs4 import BeautifulSoup
import ftplib
import argparse
import atexit
import filelock
import operator
from sklearn import tree
import pydotplus
import re
import yaml 

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/data/upload'
#app.debug = 'True'
with open('config.yaml') as config:
	config_map = yaml.safe_load(config)
sendgrid_api_key = config_map['sendgrid_api_key']
mouse_gtf = config_map['genome_files']
ip = config_map['ip']
original_directory = os.getcwd()
downloading_mutex = filelock.FileLock(original_directory+"/GEO_access.lock")


def send_email(email_to,email_from,email_subject,email_body):
	sg_client = sendgrid.SendGridAPIClient(apikey=sendgrid_api_key)
	to_email = Email(email_to)
	from_email = Email(email_from)
	content = Content('text/html',email_body)
	mail = Mail(from_email, email_subject, to_email, content)
	response = sg_client.client.mail.send.post(request_body=mail.get())
	#message = sendgrid.Mail()
	#message.add_to(email_to)
	#message.set_from(email_from)
	#message.set_subject(email_subject)
	#message.set_html(email_body)
	#client.send(message)
def create_dataset(label,data):
	single_dataset = {}
	rgb_str = randomcolor.RandomColor().generate(format_='rgb')[0]
	primary_rgba_str = rgb_str[0:3]+'a'+rgb_str[3:-1]+',1)'
	fill_rgba_str = rgb_str[0:3]+'a'+rgb_str[3:-1]+',0.2)'
	single_dataset['label'] = label
	single_dataset['backgroundColor'] = fill_rgba_str
	single_dataset['borderColor'] = primary_rgba_str
	single_dataset['pointColor'] = primary_rgba_str
	single_dataset['pointStrokeColor'] = '#fff'
	single_dataset['pointBorderColor'] = primary_rgba_str
	single_dataset['pointHoverBackgroundColor'] = primary_rgba_str
	single_dataset['pointHoverBorderColor'] = primary_rgba_str	
	#single_dataset['pointHighlightFill'] = '#fff'
	#single_dataset['pointHighlightStroke'] = primary_rgba_str
	single_dataset['data'] = data
	return single_dataset

def create_quality_check_dataset(quality_check_file):
	datasets = []	
	with open(quality_check_file) as quality_check:
		quality_check.readline()
		previous_sample = ''
		sample_information = {}
		for single_replicate in quality_check:
			line_elements = single_replicate.split("\t")
			sample_name = line_elements[1]
			avereage_base_score = line_elements[2]
			deduplication_percentage = line_elements[3]
			single_point = {}
			single_point['x'] = round(float(deduplication_percentage),2)
			single_point['y'] = round(float(avereage_base_score),2)
			single_point['r'] = 7
			if sample_name not in sample_information:
				sample_information[sample_name] = []
			sample_information[sample_name].append(single_point)
	for single_sample_name in sample_information:
		single_dataset = {}
		rgb_str = randomcolor.RandomColor().generate(format_='rgb')[0]
		primary_rgba_str = rgb_str[0:3]+'a'+rgb_str[3:-1]+',1)'
		single_dataset['label'] = single_sample_name
		single_dataset['data'] = sample_information[single_sample_name]
		single_dataset['backgroundColor'] = primary_rgba_str
		single_dataset['hoverBackgroundColor'] = primary_rgba_str
		datasets.append(single_dataset)
	data = {'datasets':datasets}
	return data




def parse_input_str(input_str):
	#remove any whitespace
	input_str_no_whitespace = "".join(input_str.split())
	input_elements = input_str_no_whitespace.split(',')
	index_list = []
	for single_element in input_elements:
		range_list = []
		if single_element != '':
			if '-' in single_element:
				range_nums = single_element.split('-')
				if len(range_nums) != 2:
					return "You should only have 2 numbers between -"
				else:
					lower_num = range_nums[0]
					higher_num = range_nums[1]
					if not lower_num.isdigit():
						return "You have a non-digit input: '"+str(lower_num)
					if not higher_num.isdigit():
						return "You have a non-digit input: "+str(higher_num)
					range_list = range(int(lower_num),int(higher_num)+1)
			else:
				if not single_element.isdigit():
					return "You have a non-digit input: " + str(single_element)
				else:
					range_list = [int(single_element)]
			index_list = index_list + range_list
	return list(set(index_list))

def convert_file_to_html_table(file_name):
	html_file = '<table class="pure-table pure-table-striped">'
	with open(file_name) as file_pointer:
		html_file = html_file + '<tr>'
		header_line = file_pointer.readline()
		header_name_list = ['#'] + header_line.split('\t')
		for single_header in header_name_list:
			html_file = html_file + '<th>'+str(single_header)+'</th>'
		html_file = html_file + '</tr>'
		for single_line in file_pointer:
			line_elements = single_line.split('\t')
			html_file = html_file + '<tr>'
			for single_element in line_elements:
				html_file = html_file + '<td>'+str(single_element)+'</td>'
			html_file = html_file + '</tr>'
	html_file = html_file + '</table>'
	return html_file

def convert_non_numbered_file_to_html_table(file_name):
	html_file = '<table class="pure-table pure-table-striped">'
	with open(file_name) as file_pointer:
		html_file = html_file + '<tr>'
		header_line = file_pointer.readline()		
		header_name_list = ['#'] + header_line.split('\t')
		for single_header in header_name_list:
			html_file = html_file + '<th>'+str(single_header)+'</th>'
		html_file = html_file + '</tr>'
		count = 0
		for single_line in file_pointer:
			line_elements = single_line.split('\t')
			html_file = html_file + '<tr><td>'+str(count)+'</td>'			
			for single_element in line_elements:
				html_file = html_file + '<td>'+str(single_element)+'</td>'
			count = count + 1
			html_file = html_file + '</tr>'
	html_file = html_file + '</table>'
	return html_file

def convert_gene_list_to_table(gene_list):
	html_file = '<table class="pure-table pure-table-striped"><tr><th>#</th><th>Gene Name</th><th>Value</th></tr>'
	counter = 1
	for single_elem in gene_list:
		html_file = html_file + '<tr><td>'+str(counter)+'</td><td>'+str(single_elem[0])+'</td><td>'+str(single_elem[1])+'</td></tr>'
		counter = counter+1
	html_file = html_file+'</table>'
	return html_file

def parse_graph_data(input_str,gini_cutoff):	
	input_str_lines = input_str.split('\n')
	is_first = True
	gene_dict = {} 
	for single_line in input_str_lines:
		if 'label=<' in single_line and 'label=<gini' not in single_line:			
			sections = single_line.split('<br/>')
			gene_name = sections[0].split('<')[1].split(' ')[0]
			gini_value = float(sections[1][7:])
			group_label = sections[4].split('>')[0][8:]
			if is_first:
				is_first = False
				gene_dict[gene_name] = group_label
			else:
				if gini_value > gini_cutoff:
					gene_dict[gene_name] = group_label
	print gene_dict
	return gene_dict

@app.route('/',methods=['GET'])
def get_main_page():
	return render_template('index.html')
@app.route('/single_cell_rna',methods=['GET'])
def show_single_cell_rna():
	return render_template('single_cell_page.html')
@app.route('/rna',methods=['GET'])
def show_rna():
	return render_template('standard_rna_seq_page.html')
@app.route('/normalize',methods=['GET'])
def get_input_data():
	genome_list = config_map['genome_files']
	library_type_list = config_map['library-type']
	genome_name_list_html = ''
	library_type_name_list = ''
	for single_library_item in library_type_list:
		library_type_name_list = library_type_name_list + '<option>'+single_library_item+'</option>' 
	for single_genome_item in genome_list:
		genome_name_list_html = genome_name_list_html + '<option>'+single_genome_item['name']+'</option>'

	
	return render_template('input_data.html',genome_name_list_html=genome_name_list_html, library_type_name_list=library_type_name_list)
@app.route('/normalize',methods=['POST'])
def get_normalized_experiment():
	#original_directory = os.getcwd()
	
	found_experiment_id = False
	condition_dict = {}
	#Get expereminet Id
	while found_experiment_id == False:
		experiment_id = randint(10000,99999)
		folder_path = original_directory+'/data/normalize/'+str(experiment_id)
		if os.path.isdir(folder_path):
			continue
		else:
			found_experiment_id = True
	#move into the experiment directory
	os.makedirs(folder_path)
	print folder_path	
	#os.chdir(folder_path)
	#handle urls and condition names
	for single_key in request.form:
		split_str = single_key.split('_')
		if 'name' in single_key:
			if 'user' not in single_key:
				condition_dict[split_str[1]] = request.form[single_key]
		else:
			if 'user' not in single_key:

				sample_path = folder_path +'/condition_'+split_str[1]+'/sample_'+split_str[3]				
				sample_url = request.form[single_key]
				if '://' not in sample_url:
					correct_url = 'http://'+sample_url
				else:
					correct_url = sample_url.replace('ftp://','http://')
				downloading_mutex.acquire()				
				try:
					os.makedirs(sample_path)
					os.chdir(sample_path)
					print correct_url
					split_url = correct_url.split('/')
					response = requests.get(correct_url, stream=True)
					print response
					#print response.text
					if response.encoding == 'utf-8' or response.status_code >= 400:
						print response.encoding
						print response.status_code
						error_response = "The Url: " + correct_url + " for "+single_key+" is not valid."
						os.chdir(original_directory)
						shutil.rmtree(folder_path)
						return render_template('error.html',error_text=error_response)

					with open(split_url[-1],'wb') as sample_file:
						shutil.copyfileobj(response.raw,sample_file)
					del response
					print "downloaded file"
					time.sleep(1.5)
				except:
					error_response = "The Url: " + correct_url + " for "+single_key+" is not valid."
					print sys.exc_info()
					os.chdir(original_directory)
					shutil.rmtree(folder_path)
					return render_template('error.html',error_text=error_response)
				finally:
					downloading_mutex.release()
	#os.chdir(folder_path)

	

	#sort the conditions by number
	#sorted_condition_tuple = sorted(condition_dict.items(), key=operator.itemgetter(1))
	#condition_list = []
	#full_condition_list = 'Condition Name\n'
	#for single_tuple in sorted_condition_tuple:
	#	condition_element = ' '.join(map(str,single_tuple))
	#	condition_list.append(condition_element)
	#full_condition_list = '\n'.join(condition_list)
	#print full_condition_list
	#save condition names into a file
	
	form_files = request.files
	for single_file_key in form_files:
		split_str = single_file_key.split('_')
		sample_path = folder_path +'/condition_'+split_str[1]+'/sample_'+split_str[3]
		downloading_mutex.acquire()
		try:
			os.makedirs(sample_path)
			os.chdir(sample_path)		
			single_file = form_files[single_file_key]
			if '.sra' not in single_file.filename:
				error_response = "The file: " + single_file.filename + " for "+single_file_key+" is not a valid sra file."
				os.chdir(original_directory)
				shutil.rmtree(folder_path)
				return render_template('error.html',error_text=error_response)
			single_file.save(secure_filename(single_file.filename))
		except:
			print sys.exc_info()
			os.chdir(original_directory)
			shutil.rmtree(folder_path)
			return render_template('error.html',error_text='There was an error processing your files, please check the server logs')
		finally:
			downloading_mutex.release()


	#os.chdir(folder_path)
	for condition_num in condition_dict:
		condition_path = folder_path+'/condition_'+str(condition_num)
		if os.path.isdir(condition_path) == False:
			error_response = "The condition: " + condition_dict[condition_num] + " is missing a sample."
			os.chdir(original_directory)
			shutil.rmtree(folder_path)
			return render_template('error.html',error_text=error_response)	
	#os.chdir(original_directory+'/data/upload')
	#print os.getcwd()
	user_info_dict = {}
	user_info_dict['user_name'] = request.form['user_name']
	user_info_dict['user_email'] = request.form['user_email']
	experiment_info_dict = {}
	experiment_info_dict['genome'] = request.form['genome']
	experiment_info_dict['library_type'] = request.form['library_type']


	with open(folder_path+'/condition_names.json','w') as condition_names:
		json.dump(condition_dict,condition_names)
	with open(folder_path+'/user_info.json','w') as user_info:
		json.dump(user_info_dict,user_info)
	with open(folder_path+'/experiment_info.json','w') as experiment_info:
		json.dump(experiment_info_dict,experiment_info)
	
	#os.chdir(original_directory)
	client = MongoClient('mongodb://localhost:27017/')
	experiment_db = client.experiment_database
	norm_collection =experiment_db.normalize_collection
	experiment_queue = norm_collection.find_one({'name':'experiment_queue'})
	if experiment_queue == None:
		new_queue = []
		new_queue.append(experiment_id)
		new_queue_dict = {'name':'experiment_queue','data':new_queue}
		norm_collection.insert_one(new_queue_dict)
	else:
		queue = experiment_queue['data']
		queue.append(experiment_id)		
		experiment_queue['data'] = queue
		norm_collection.replace_one({'name':'experiment_queue'},experiment_queue)

	os.chdir(original_directory)

	email_body = 'Dear '+ user_info_dict['user_name']+'<br> This is a confirmation message that your experiment has been scheduled. The id for your experiment is ' + str(experiment_id)+'<br>Sincerely,<br>RnaSeqPipeline Notifier'
	send_email(user_info_dict['user_email'],'RnaSeqPipeline@rutgers.edu','Normalized Experiment Scheduled ID: '+str(experiment_id),email_body)
	html_body = 'This is a confirmation message that your experiment has been scheduled. The id for your experiment is ' + str(experiment_id) +'. A confirmation email has been sent out to '+user_info_dict['user_email']
	return render_template('success.html',success_text=html_body)
	
@app.route('/analyze/cluster',methods=['GET'])
def get_info_for_cluster():
	return render_template('input_data_cluster.html')
@app.route('/analyze/cluster',methods=['POST'])
def get_cluster():
	#original_directory = os.getcwd()
	experiment_id = request.form['experiment_id']
	cluster_num = request.form['num_clusters']
	folder_path = original_directory+'/data/normalize/'+str(experiment_id)+'/cnout'
	script_path = original_directory+'/RScripts/cell_cluster.r'
	if os.path.isdir(folder_path) == False:
		return render_template('error.html',error_text='The experiment id is invalid or did not finish yet')
	if not os.path.exists(folder_path+'/post_quality_control_data.rds'):
		return render_template('error.html',error_text='The quality control dataset does not exist for this experiment. Please run the quality control program first')
	#os.chdir(folder_path)
	#Rscript ~/RNASeqPipeline/RScripts/cell_cluster.r 3
	subprocess.Popen(['Rscript',script_path,cluster_num],cwd=folder_path).wait()
	output_figure = folder_path+'/cell_cluster_plot.png'
	output_figure_tiff = folder_path+'/cell_cluster_plot.tiff'
	figure_destination_folder = original_directory+'/static/data/normalize/'+str(experiment_id)+'/'
	output_text = folder_path+'/cluster_table_after.txt'
	html_table = convert_file_to_html_table(output_text)
	shutil.copy(output_figure,figure_destination_folder)
	shutil.copy(output_figure_tiff,figure_destination_folder)
	figure_link = '/static/data/normalize/'+str(experiment_id)+'/cell_cluster_plot.png'
	#os.chdir(original_directory)	
	return render_template('show_figure_and_samples.html',image_link=figure_link,html_table=html_table)
@app.route('/analyze/classify',methods=['GET'])
def get_info_for_classify():
	return render_template('input_data_classify.html')
@app.route('/analyze/classify',methods=['POST'])
def get_classify():
	#original_directory = os.getcwd()
	experiment_id = request.form['experiment_id']
	folder_path = original_directory+'/data/normalize/'+str(experiment_id)+'/cnout'
	if os.path.isdir(folder_path) == False:
		return render_template('error.html',error_text='The experiment id is invalid or did not finish yet')
	if not os.path.exists(folder_path+'/post_quality_control_data.rds'):
		return render_template('error.html',error_text='The quality control dataset does not exist for this experiment. Please run the quality control program first')
	#os.chdir(folder_path)
	gene_short_name_list = []
	with open(folder_path+'/genes.attr_table') as gene_attr_file:
		for line in gene_attr_file:
			gene_short_name = line.split("\t")[4]
			if gene_short_name != 'gene_short_name':
				gene_short_name_list.append(gene_short_name)

	label_done = False	
	label_num = 1
	label_list = []
	R_cell_classify = R_start_monocle + 'cth <- newCellTypeHierarchy()\n'
	while label_done == False:
		label_key = 'label_'+str(label_num)+'_name'
		if label_key in request.form:			
			condition_num = 1
			gene_conditions_str = ""
			condition_done = False
			while condition_done == False:
				condition_key = 'label_'+str(label_num)+'_condition_'+str(condition_num)+'_type'
				#print condition_num
				#print label_num
				if condition_key in request.form:
					if condition_num == 1:
						gene_condition_name_key = 'label_'+str(label_num)+'_condition_'+str(condition_num)+'_first_gene'
						gene_condition_type_key = 'label_'+str(label_num)+'_condition_'+str(condition_num)+'_type'
						gene_condition_num_key = 'label_'+str(label_num)+'_condition_'+str(condition_num)+'_num'
						gene_condition_name = request.form[gene_condition_name_key]						
						if gene_condition_name not in gene_short_name_list:
							#os.chdir(original_directory)
							return render_template('error.html',error_text='The gene short name '+gene_condition_name+' does not exist in the attribute table [genes.attr_table]')
						gene_conditions_str = gene_conditions_str + 'x['+gene_condition_name+'_id,] ' + request.form[gene_condition_type_key] + ' '+request.form[gene_condition_num_key]
						R_cell_classify = R_cell_classify + gene_condition_name+'_id <- row.names(subset(fData(HSMM), gene_short_name == "'+gene_condition_name+'"))\n'
					else:
						gene_condition_name_and_key = 'label_'+str(label_num)+'_condition_'+str(condition_num)+'_and_gene'
						gene_condition_name_or_key = 'label_'+str(label_num)+'_condition_'+str(condition_num)+'_or_gene'
						gene_condition_type_key = 'label_'+str(label_num)+'_condition_'+str(condition_num)+'_type'
						gene_condition_num_key = 'label_'+str(label_num)+'_condition_'+str(condition_num)+'_num'
						if gene_condition_name not in gene_short_name_list:
							#os.chdir(original_directory)
							return render_template('error.html',error_text='The gene short name '+gene_condition_name+' does not exist in the attribute table [genes.attr_table]')						
						if gene_condition_name_and_key in request.form:
							gene_condition_name = request.form[gene_condition_name_and_key]
							gene_conditions_str = gene_conditions_str + ' & x['+gene_condition_name+'_id,] ' + request.form[gene_condition_type_key] + ' '+request.form[gene_condition_num_key]							
						if gene_condition_name_or_key in request.form:
							gene_condition_name = request.form[gene_condition_name_or_key]
							gene_conditions_str = gene_conditions_str + ' | x['+gene_condition_name+'_id,] ' + request.form[gene_condition_type_key] + ' '+request.form[gene_condition_num_key]
						R_cell_classify = R_cell_classify + gene_condition_name+'_id <- row.names(subset(fData(HSMM), gene_short_name == "'+gene_condition_name+'"))\n'
				else:
					condition_done = True
					label_name = request.form[label_key]
					R_cell_classify = R_cell_classify +'cth <- addCellType(cth, "'+label_name+'", classify_func=function(x) {'+gene_conditions_str+'})\n'
					if label_name in label_list:
						#os.chdir(original_directory)
						return render_template('error.html',error_text='There label name '+label_name+' is used more than once')
					continue
				condition_num = condition_num + 1
		else:
			label_done = True
			continue
		label_num = label_num + 1
	R_cell_classify = R_cell_classify + 'HSMM <- classifyCells(HSMM, cth, 0.1)\nprint(plot_cell_trajectory(HSMM, color="CellType"))\nggsave("cell_classify_plot.png")\nggsave("cell_classify_plot.tiff", width = 7, height = 7,dpi=600)\nsaveRDS(HSMM,"classified_cells.rds")\npData(HSMM)$Size_Factor <- NULL\nrownames(pData(HSMM)) <- NULL\npData(HSMM)$Total_mRNAs <- Matrix::colSums(exprs(HSMM))\nwrite.table(pData(HSMM), "classification_after.txt", sep="\t",quote=FALSE)'
	with open(folder_path+'/cell_classify.r','w') as R_script:
		R_script.write(R_cell_classify)
	script_path = folder_path+'/cell_classify.r'	
	subprocess.Popen(['Rscript',script_path],cwd=folder_path).wait()
	#os.chdir(original_directory)
	figure_destination_folder = original_directory+'/static/data/normalize/'+str(experiment_id)+'/'
	output_figure = folder_path+'/cell_classify_plot.png'
	output_figure_tiff = folder_path+'/cell_classify_plot.tiff'
	shutil.copy(output_figure,figure_destination_folder)
	shutil.copy(output_figure_tiff,figure_destination_folder)
	output_text = folder_path+'/classification_after.txt'
	figure_link = '/static/data/normalize/'+str(experiment_id)+'/cell_classify_plot.png'
	html_table = convert_file_to_html_table(output_text)
	return render_template('show_classification.html',image_link=figure_link,html_table=html_table)
@app.route('/analyze/classified_cluster',methods=['GET'])
def get_info_for_classified_cluster():
	return render_template('input_data_classified_cluster.html')
@app.route('/analyze/classified_cluster',methods=['POST'])
def get_classified_cluster():
	#original_directory = os.getcwd()
	experiment_id = request.form['experiment_id']
	cluster_num = request.form['num_clusters']
	folder_path = original_directory+'/data/normalize/'+str(experiment_id)+'/cnout'
	print folder_path	
	script_path = original_directory+'/RScripts/cell_classified_cluster.r'
	if os.path.isdir(folder_path) == False:
		return render_template('error.html',error_text='The experiment id is invalid or did not finish yet')
	if not os.path.exists(folder_path+'/classified_cells.rds'):
		return render_template('error.html',error_text='The classified dataset does not exist for this experiment. You need to create one.')
	#os.chdir(folder_path)
	#Rscript ~/RNASeqPipeline/RScripts/cell_classified_cluster.r 3
	subprocess.call(['Rscript',script_path,cluster_num])
	output_figure = folder_path+'/cell_classified_cluster_plot.png'
	figure_destination_folder = original_directory+'/static/data/normalize/'+str(experiment_id)+'/'
	shutil.copy(output_figure,figure_destination_folder)
	figure_link = '/static/data/normalize/'+str(experiment_id)+'/cell_classified_cluster_plot.png'
	os.chdir(original_directory)	
	return render_template('show_figure.html',image_link=figure_link)
@app.route('/analyze/cell_trajectory',methods=['GET'])
def get_info_for_cell_trajectory():
	return render_template('input_data_cell_trajectory.html')
@app.route('/analyze/cell_trajectory',methods=['POST'])
def get_cell_trajectory():
	#original_directory = os.getcwd()
	experiment_id = request.form['experiment_id']
	dimension_num = request.form['num_dimensions']
	folder_path = original_directory+'/data/normalize/'+str(experiment_id)+'/cnout'	
	script_path = original_directory+'/RScripts/cell_classified_trajectory.r'
	if os.path.isdir(folder_path) == False:
		return render_template('error.html',error_text='The experiment id is invalid or did not finish yet')
	if not os.path.exists(folder_path+'/classified_cells.rds'):
		return render_template('error.html',error_text='The classified dataset does not exist for this experiment. You need to create one.')
	#os.chdir(folder_path)
	#Rscript ~/RNASeqPipeline/RScripts/cell_classified_cluster.r 3
	subprocess.Popen(['Rscript',script_path,dimension_num],cwd=folder_path).wait()
	output_figure = folder_path+'/cell_classified_trajectory_plot.png'
	output_figure_tiff = folder_path+'/cell_classified_trajectory_plot.tiff'
	figure_destination_folder = original_directory+'/static/data/normalize/'+str(experiment_id)+'/'
	shutil.copy(output_figure,figure_destination_folder)
	shutil.copy(output_figure_tiff,figure_destination_folder)
	figure_link = '/static/data/normalize/'+str(experiment_id)+'/cell_classified_trajectory_plot.png'
	#os.chdir(original_directory)	
	return render_template('show_figure.html',image_link=figure_link)
@app.route('/analyze/cell_pseudotime',methods=['GET'])
def get_info_for_cell_pseudotime():
	return render_template('input_data_cell_pseudotime.html')
@app.route('/analyze/cell_pseudotime', methods=['POST'])
def get_cell_pseudotime():
	#original_directory = os.getcwd()
	experiment_id = request.form['experiment_id']
	num_dimensions = request.form['num_dimensions']
	folder_path = original_directory+'/data/normalize/'+str(experiment_id)+'/cnout'	
	script_path = original_directory+'/RScripts/cell_classified_pseudotime.r'
	if os.path.isdir(folder_path) == False:
		return render_template('error.html',error_text='The experiment id is invalid or did not finish yet')
	if not os.path.exists(folder_path+'/classified_cells.rds'):
		return render_template('error.html',error_text='The classified dataset does not exist for this experiment. You need to create one.')
	#os.chdir(folder_path)
	gene_short_name_list = []
	with open(folder_path+'/genes.attr_table') as gene_attr_file:
		for line in gene_attr_file:
			gene_short_name = line.split("\t")[4]
			if gene_short_name != 'gene_short_name':
				gene_short_name_list.append(gene_short_name)
	command = ['Rscript',script_path]	
	command.append(num_dimensions)
	for single_key in request.form:
		if 'gene' in single_key:
			gene_name = request.form[single_key]
			if gene_name not in gene_short_name_list:
				#os.chdir(original_directory)
				return render_template('error.html',error_text='The gene short name '+gene_name+' does not exist in the attribute table [genes.attr_table]')
			else:
				command.append(gene_name)
	subprocess.Popen(command,cwd=folder_path).wait()
	output_figure = folder_path+'/cell_classified_pseudotime_plot.png'
	output_figure_tiff = folder_path+'/cell_classified_pseudotime_plot.tiff'
	figure_destination_folder = original_directory+'/static/data/normalize/'+str(experiment_id)+'/'
	shutil.copy(output_figure,figure_destination_folder)
	shutil.copy(output_figure_tiff,figure_destination_folder)
	figure_link = '/static/data/normalize/'+str(experiment_id)+'/cell_classified_pseudotime_plot.png'
	#os.chdir(original_directory)	
	return render_template('show_figure.html',image_link=figure_link)

@app.route('/analyze/cell_genes',methods=['GET'])
def get_info_cell_genes():
	return render_template('input_data_cell_genes.html')
@app.route('/analyze/cell_genes',methods=['POST'])
def get_cell_genes():
	experiment_id = request.form['experiment_id']
	folder_path = original_directory+'/data/normalize/'+str(experiment_id)+'/cnout'	
	script_path = original_directory+'/RScripts/cell_classified_genes.r'
	if os.path.isdir(folder_path) == False:
		return render_template('error.html',error_text='The experiment id is invalid or did not finish yet')
	if not os.path.exists(folder_path+'/classified_cells.rds'):
		return render_template('error.html',error_text='The classified dataset does not exist for this experiment. Please run the classification program first')
	#os.chdir(folder_path)
	gene_short_name_list = []
	with open(folder_path+'/genes.attr_table') as gene_attr_file:
		for line in gene_attr_file:
			gene_short_name = line.split("\t")[4]
			if gene_short_name != 'gene_short_name':
				gene_short_name_list.append(gene_short_name)
	command = ['Rscript',script_path]	
	for single_key in request.form:
		if 'gene' in single_key:
			gene_name = request.form[single_key]
			if gene_name not in gene_short_name_list:
				#os.chdir(original_directory)
				return render_template('error.html',error_text='The gene short name '+gene_name+' does not exist in the attribute table [genes.attr_table]')
			else:
				command.append(gene_name)
	subprocess.Popen(command,cwd=folder_path).wait()
	output_figure = folder_path+'/cell_classified_genes_plot.png'
	output_figure_tiff = folder_path+'/cell_classified_genes_plot.tiff'
	figure_destination_folder = original_directory+'/static/data/normalize/'+str(experiment_id)+'/'
	shutil.copy(output_figure,figure_destination_folder)
	shutil.copy(output_figure_tiff,figure_destination_folder)
	figure_link = '/static/data/normalize/'+str(experiment_id)+'/cell_classified_genes_plot.png'
	#os.chdir(original_directory)	
	return render_template('show_figure.html',image_link=figure_link)
@app.route('/server_status',methods=['GET'])
def get_server_status():
	client = MongoClient('mongodb://localhost:27017/')
	experiment_db = client.experiment_database
	status_collection =experiment_db.server_status_collection
	status_database_dict = status_collection.find_one({'name':'server_status_dict'})
	if status_database_dict == None:
		return render_template('error.html',error_text='The status dataset is empty. The server_status script does not seem to be running')
	else:
		status_dict = status_database_dict['data']
		temp_dict = status_dict['temps']
		cpu_dict = status_dict['cpu']
		network_list = status_dict['network']		
		disk_list = status_dict['disk']
		memory_list = status_dict['memory']
		load_list = status_dict['load']
		i = 0
		relative_network = []
		while i < len(network_list) - 1:
			network_difference = round(float(network_list[i+1]) - float(network_list[i]),2)
			relative_network.append(network_difference)
			i = i + 1
		temp_data = {}
		cpu_data = {}
		network_data = {}
		disk_data = {}
		memory_data = {}
		load_data = {}
		temp_datasets = []
		cpu_datasets = []
		critical_temp = temp_dict['critical_temp']
		temp_length = 0
		cpu_length = 0
		single_dataset = {}
		crit_dataset = {}
		for temp_elem in temp_dict:
			if temp_elem == 'critical_temp':
				continue				
			else:
				single_dataset = create_dataset(temp_elem,temp_dict[temp_elem])				
				temp_length = len(temp_dict[temp_elem])
				temp_datasets.append(single_dataset)
		for cpu_elem in cpu_dict:
			single_cpu_dataset = create_dataset(cpu_elem,cpu_dict[cpu_elem])
			cpu_length = len(cpu_dict[cpu_elem])
			cpu_datasets.append(single_cpu_dataset)

		temp_x = range(0,temp_length)
		rgb_str = randomcolor.RandomColor().generate(format_='rgb')[0]
		primary_rgba_str = rgb_str[0:3]+'a'+rgb_str[3:-1]+',1)'
		
		crit_dataset['label'] = 'Critical Temp'
		crit_dataset['borderColor'] = primary_rgba_str
		crit_dataset['pointColor'] = primary_rgba_str
		crit_dataset['pointStrokeColor'] = primary_rgba_str
		crit_dataset['pointBorderColor'] = primary_rgba_str
		crit_dataset['pointHoverBackgroundColor'] = primary_rgba_str
		crit_dataset['pointHoverBorderColor'] = primary_rgba_str		
		crit_dataset['data'] = [critical_temp]*temp_length
		temp_datasets.append(crit_dataset)
		temp_data['labels'] = temp_x[::-1]
		temp_data['datasets'] = temp_datasets
		cpu_data['labels'] = range(0,cpu_length)[::-1]
		cpu_data['datasets'] = cpu_datasets
		network_data['labels'] = range(0,len(relative_network))[::-1]
		network_data['datasets'] = [create_dataset('Network',relative_network)]
		disk_data['labels'] = range(0,len(disk_list))[::-1]
		disk_data['datasets'] = [create_dataset('Disk',disk_list)]
		memory_data['labels'] = range(0,len(memory_list))[::-1]
		memory_data['datasets'] = [create_dataset('Memory',memory_list)]
		load_data['labels'] = range(0,len(load_list))[::-1]
		load_data['datasets'] = [create_dataset('Load',load_list)]
		return render_template('show_status.html',temp_data=temp_data,cpu_data=cpu_data,network_data=network_data,disk_data=disk_data,memory_data=memory_data,load_data=load_data)
@app.route('/user_info',methods=['GET'])
def get_user_info():
	client = MongoClient('mongodb://localhost:27017/')
	experiment_db = client.experiment_database
	norm_collection =experiment_db.normalize_collection
	diff_collection =experiment_db.diff_collection
	quality_collection = experiment_db.quality_collection

	experiment_queue = norm_collection.find_one({'name':'experiment_queue'})
	experiment_queue1 = diff_collection.find_one({'name':'experiment_queue'})
	experiment_queue2 = quality_collection.find_one({'name':'experiment_queue'})
	#quality_collection.drop()
	print experiment_queue2
	html_response = ""
	if experiment_queue == None:
		html_response = "<p>The queue is currently empty</p>"
	else:
		queue = experiment_queue['data']
		if len(queue) == 0:
			html_response = "<p>The queue is currently empty</p>"
		else:
			html_response = '<table class="pure-table pure-table-striped"><tr><th>#</th><th>Experiment Id</th><th>User Name</th></tr>'
			experiment_num = 0		
			for single_id in queue:
				user_file_path = original_directory+'/data/normalize/'+str(single_id)+'/user_info.json'
				with open(user_file_path) as user_info_data:
					user_name = json.load(user_info_data)['user_name']
				html_response = html_response+'<tr><td>'+str(experiment_num)+'</td><td>'+str(single_id)+'</td><td>'+str(user_name)+'</td></tr>'
				experiment_num = experiment_num + 1
			html_response = html_response+'</table>'
	if experiment_queue1 == None:
		html_response1 = "<p>The queue is currently empty</p>"
	else:
		queue = experiment_queue1['data']
		if len(queue) == 0:
			html_response1 = "<p>The queue is currently empty</p>"
		else:
			html_response1 = '<table class="pure-table pure-table-striped"><tr><th>#</th><th>Experiment Id</th><th>User Name</th></tr>'
			experiment_num = 0
			for single_id in queue:
				user_file_path = original_directory+'/data/diff/'+str(single_id)+'/user_info.json'
				with open(user_file_path) as user_info_data:
					user_name = json.load(user_info_data)['user_name']
				html_response1 = html_response1+'<tr><td>'+str(experiment_num)+'</td><td>'+str(single_id)+'</td><td>'+str(user_name)+'</td></tr>'
				experiment_num = experiment_num + 1
			html_response1 = html_response1+'</table>'
	if experiment_queue2 == None:
		html_response2 = "<p>The queue is currently empty</p>"
	else:
		queue = experiment_queue2['data']
		if len(queue) == 0:
			html_response2 = "<p>The queue is currently empty</p>"
		html_response2 = '<table class="pure-table pure-table-striped"><tr><th>#</th><th>GEO Num</th><th>User Name</th></tr>'
		experiment_num = 0
		for single_id in queue:
			html_response2 = html_response2+'<tr><td>'+str(experiment_num)+'</td><td>'+str(single_id['geo_number'])+'</td><td>'+str(single_id['user_name'])+'</td></tr>'
			experiment_num = experiment_num + 1
		html_response2 = html_response2+'</table>'
	return render_template('show_experiment_queue.html',norm_table=html_response,diff_table=html_response1,quality_table=html_response2)
@app.route('/quality_check_page',methods=['GET'])
def get_quality_check_page():
	return render_template('check_GEO_quality_page.html')
@app.route('/check_quality',methods=['GET'])
def get_info_quality_check():
	return render_template('input_data_quality_check.html')
@app.route('/check_quality',methods=['POST'])
def get_quality_check():
	GEO_number = request.form['geo_number']
	user_name = request.form['user_name']
	user_email = request.form['user_email']

	html_file = requests.get('https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=' + str(GEO_number)).text
	soup = BeautifulSoup(html_file, 'html.parser')
	link_list = []
	sample_name = ''
	for single_link in soup.find_all('a'):
		if 'geo/query/acc.cgi?acc=' in single_link.get('href') and 'GSM' in single_link.get('href'):
			link_list.append(single_link.get('href'))
	if len(link_list) == 0:
		return render_template('error.html',error_text='The geo number '+GEO_number+' is invalid.')

	quality_check_file = GEO_number  + '_Quality_Check.xls'
	if os.path.isfile(quality_check_file):		
		os.remove(quality_check_file)

	client = MongoClient('mongodb://localhost:27017/')
	experiment_db = client.experiment_database
	quality_collection =experiment_db.quality_collection
	quality_queue = quality_collection.find_one({'name':'experiment_queue'})
	new_element = {'geo_number':GEO_number,'user_name':user_name,'user_email':user_email}
	if quality_queue == None:
		new_queue = []
		new_queue.append(new_element)
		new_queue_dict = {'name':'experiment_queue','data':new_queue}
		quality_collection.insert_one(new_queue_dict)
	else:
		queue = quality_queue['data']
		queue.append(new_element)		
		quality_queue['data'] = queue
		quality_collection.replace_one({'name':'experiment_queue'},quality_queue)
	email_body = 'Dear '+ user_name+'<br> This is a confirmation message that your quality check analysis for '+str(GEO_number)+' has been scheduled.<br>Sincerely,<br>RnaSeqPipeline Notifier'
	send_email(user_email,'RnaSeqPipeline@rutgers.edu','Started Quality Check Analysis for GEO number: '+str(GEO_number),email_body)
	html_body = 'This is a confirmation message that your quality check analysis for '+str(GEO_number)+' has been scheduled. A confirmation email has been sent out to '+user_email
	return render_template('success.html',success_text=html_body)
@app.route('/analyze/significant_genes_id',methods=['GET'])
def get_info_experiment_id():
	return render_template('input_data_experiment_id.html',function_name='get_info_significant_genes')
@app.route('/analyze/significant_genes_id',methods=['POST'])
def get_info_significant_genes():
	experiment_id = request.form['experiment_id']
	folder_path = original_directory+'/data/normalize/'+str(experiment_id)+'/cnout'
	script_path = original_directory+'/RScripts/get_pheno_data.r'
	if os.path.isdir(folder_path) == False:
		return render_template('error.html',error_text='The experiment id is invalid or did not finish yet')
	#os.chdir(folder_path)
	#Rscript ~/RNASeqPipeline/RScripts/get_pheno_data.r
	subprocess.Popen(['Rscript',script_path],cwd=folder_path).wait()
	output_text = folder_path+'/pData_table.txt'
	html_table = convert_file_to_html_table(output_text)
	return render_template('input_data_significant_genes.html',html_table=html_table,experiment_id=experiment_id)
@app.route('/analyze/significant_genes',methods=['POST'])
def get_significant_genes():
	experiment_id = request.form['experiment_id']
	group_1 = request.form['group_1']
	group_2 = request.form['group_2']
	group_1_list = parse_input_str(group_1)
	if isinstance(group_1_list,basestring):
		return render_template('error.html',error_text=group_1_list)
	group_2_list = parse_input_str(group_2)
	if isinstance(group_2_list,basestring):
		return render_template('error.html',error_text=group_2_list)
	gene_fkpm_file =  original_directory+'/data/normalize/'+str(experiment_id)+'/cnout/genes.fpkm_table'
	genes_dict = {}
	with open(gene_fkpm_file) as fpkm_file:
		header_line = fpkm_file.readline()
		for single_line in fpkm_file:
			line_split = single_line.split()
			first_list = []
			second_list = []
			for first_location in group_1_list:
				if first_location >= len(line_split):
					first_list.append(0)
				else:
					first_list.append(float(line_split[first_location]))
			for second_location in group_2_list:
				if second_location >= len(line_split):
					second_list.append(0)
				else:
					second_list.append(float(line_split[second_location]))
			first_avg = sum(first_list)/float(len(first_list))
			second_avg = sum(second_list)/float(len(second_list))
			#print first_avg
			#print second_avg
			genes_dict[line_split[0]] = first_avg - second_avg
	sorted_genes = sorted(genes_dict.items(), key=operator.itemgetter(1))
	higher_group_2 = sorted_genes[0:25]
	table_group_2 = sorted_genes[0:100]
	sorted_genes.reverse()
	higher_group_1 = sorted_genes[0:25]
	table_group_1 = sorted_genes[0:100]
	group_2_data = []
	group_2_label = []
	for single_gene_elem_2 in higher_group_2:
		group_2_label.append(single_gene_elem_2[0])
		group_2_data.append(round(single_gene_elem_2[1],2))
	group_1_data = []
	group_1_label = []
	for single_gene_elem_1 in higher_group_1:
		group_1_label.append(single_gene_elem_1[0])
		group_1_data.append(round(single_gene_elem_1[1],2))
	higher_group_2_dataset = create_dataset('group 1 below group 2 expression',group_2_data)
	higher_group_1_dataset = create_dataset('group 1 over group 2 expression',group_1_data)
	higher_group_2_data = {}
	higher_group_1_data = {}
	higher_group_2_data['labels'] = group_2_label
	higher_group_2_data['datasets'] = [higher_group_2_dataset]
	higher_group_1_data['labels'] = group_1_label
	higher_group_1_data['datasets'] = [higher_group_1_dataset]
	html_table_group_2 = convert_gene_list_to_table(table_group_2)
	html_table_group_1 = convert_gene_list_to_table(table_group_1)
	return render_template('show_significant_genes.html',higher_group_1_data=higher_group_1_data,higher_group_2_data=higher_group_2_data,html_table_group_1=html_table_group_1,html_table_group_2=html_table_group_2)
@app.route('/analyze/quality_control_id',methods=['GET'])
def get_info_quality_control_id():
	return render_template('input_data_experiment_id.html',function_name='get_info_quality_control')
@app.route('/analyze/quality_control_id',methods=['POST'])
def get_info_quality_control():
	experiment_id = request.form['experiment_id']
	folder_path = original_directory+'/data/normalize/'+str(experiment_id)+'/cnout'
	script_path = original_directory+'/RScripts/get_total_mrna.r'
	if os.path.isdir(folder_path) == False:
		return render_template('error.html',error_text='The experiment id is invalid or did not finish yet')
	#os.chdir(folder_path)
	#Rscript ~/RNASeqPipeline/RScripts/get_total_mrna.r
	subprocess.Popen(['Rscript',script_path],cwd=folder_path).wait()
	output_text = folder_path+'/mRNA_table.txt'
	html_table = convert_file_to_html_table(output_text)
	return render_template('input_data_quality_control.html',html_table=html_table,experiment_id=experiment_id)
@app.route('/analyze/quality_control',methods=['POST'])
def get_quality_control():
	experiment_id = request.form['experiment_id']
	lower_bound = request.form['lower_bound']
	upper_bound = request.form['upper_bound']
	min_expression = request.form['min_expression']
	min_cells = request.form['min_cells']
	if 'inf' in upper_bound:
		upper_bound = 'Inf'
	folder_path = original_directory+'/data/normalize/'+str(experiment_id)+'/cnout'
	script_path = original_directory+'/RScripts/quality_control.r'
	#Rscript ~/RNASeqPipeline/RScripts/quality_control.r lower_bound upper_bound min_gene_expression
	if os.path.isdir(folder_path) == False:
		return render_template('error.html',error_text='The experiment id is invalid or did not finish yet')
	subprocess.Popen(['Rscript',script_path,lower_bound,upper_bound,min_expression,min_cells],cwd=folder_path).wait()
	output_text = folder_path+'/post_quality_control.txt'
	with open(folder_path+'/num_genes.txt') as num_genes_data:
		num_genes_data.readline()
		num_genes = (num_genes_data.readline().split('\t'))[1]
	html_table = convert_file_to_html_table(output_text)
	return render_template('show_quality_control.html',html_table=html_table,num_genes=num_genes)
	#os.chdir(folder_path)
	
@app.route('/analyze/trim_id',methods=['GET'])
def get_info_trim_id():
	return render_template('input_data_experiment_id.html',function_name='get_info_trim')
@app.route('/analyze/trim_id',methods=['POST'])
def get_info_trim():
	experiment_id = request.form['experiment_id']
	folder_path = original_directory+'/data/normalize/'+str(experiment_id)+'/cnout'
	script_path = original_directory+'/RScripts/get_current_data.r'	
	if os.path.isdir(folder_path) == False:
		return render_template('error.html',error_text='The experiment id is invalid or did not finish yet')
	if not os.path.exists(folder_path+'/post_quality_control_data.rds'):
		return render_template('error.html',error_text='The quality control dataset does not exist for this experiment. Please run the quality control program first')
	#os.chdir(folder_path)	
	#Rscript ~/RNASeqPipeline/RScripts/get_current_data.r rds_file table_file
	subprocess.Popen(['Rscript',script_path,'post_quality_control_data.rds','trim_table_before.txt'],cwd=folder_path).wait()
	output_text = folder_path+'/trim_table_before.txt'
	html_table = convert_file_to_html_table(output_text)
	return render_template('input_data_trim.html',html_table=html_table,experiment_id=experiment_id)
@app.route('/analyze/trim',methods=['POST'])
def get_trim():
	experiment_id = request.form['experiment_id']
	trim_range = request.form['trim_range']
	folder_path = original_directory+'/data/normalize/'+str(experiment_id)+'/cnout'
	script_path = original_directory+'/RScripts/trim_data.r'	
	if os.path.isdir(folder_path) == False:
		return render_template('error.html',error_text='The experiment id is invalid or did not finish yet')
	if not os.path.exists(folder_path+'/post_quality_control_data.rds'):
		return render_template('error.html',error_text='The quality control dataset does not exist for this experiment. Please run the quality control program first')
	trim_list = parse_input_str(trim_range)	
	if isinstance(trim_list,basestring):
		return render_template('error.html',error_text=trim_list)
	trim_str = ','.join(map(str,sorted(trim_list)))
	#os.chdir(folder_path)	
	#Rscript ~/RNASeqPipeline/RScripts/trim_data.r range
	#print trim_str 
	subprocess.Popen(['Rscript',script_path,trim_str],cwd=folder_path).wait()
	output_text = folder_path+'/trim_table_after.txt'
	html_table = convert_file_to_html_table(output_text)
	return render_template('show_trim.html',html_table=html_table)
@app.route('/analyze/quality_check',methods=['GET'])
def get_info_scatter_quality_check():
	return render_template('input_data_quality_check_scatter.html')
@app.route('/analyze/quality_check',methods=['POST'])
def get_scatter_quality_check():
	geo_number = request.form['geo_number']
	file_path = original_directory+'/static/data/quality_check/'+geo_number+'/'+geo_number+'_Quality_Check.xls'
	print file_path
	if not os.path.exists(file_path):
		return render_template('error.html',error_text='The quality check data for geo number: '+geo_number+' does not exist. You need to run it through quality check first.')
	quality_check_data = create_quality_check_dataset(file_path)
	quality_check_table = convert_non_numbered_file_to_html_table(file_path)
	return render_template('show_quality_check_scatter.html',quality_check_data=quality_check_data,geo_number=geo_number,quality_check_table=quality_check_table)
@app.route('/analyze/combine_studies',methods=['GET'])
def get_combine_studies():
	return render_template('input_data_combine_studies.html')
@app.route('/analyze/combine_studies',methods=['POST'])
def combine_studies():
	experiment_id1 = request.form['experiment_id1']
	experiment_id2 = request.form['experiment_id2']
	user_name = request.form['user_name']
	user_email = request.form['user_email']
	folder_path1 = original_directory+'/data/normalize/'+str(experiment_id1)+'/cnout'
	folder_path2 = original_directory+'/data/normalize/'+str(experiment_id2)+'/cnout'	
	if os.path.isdir(folder_path1) == False:
		return render_template('error.html', error_text='The experiment id: '+experiment_id1+' is invalid or did not finish yet')
	if os.path.isdir(folder_path2) == False:
		return render_template('error.html', error_text='The experiment id: '+experiment_id2+' is invalid or did not finish yet')

	found_experiment_id = False

	while found_experiment_id == False:
		experiment_id = randint(10000,99999)
		folder_path = os.getcwd()+'/data/normalize/'+str(experiment_id)
		if os.path.isdir(folder_path):
			continue
		else:
			found_experiment_id = True
	#move into the experiment directory
	os.makedirs(folder_path)
	user_info_dict = {}
	user_info_dict['user_name'] = request.form['user_name']
	user_info_dict['user_email'] = request.form['user_email']

	with open(folder_path+'/user_info.json','w') as user_info:
		json.dump(user_info_dict,user_info)

	sample_sheet_1_path = original_directory+'/data/normalize/'+str(experiment_id1)+'/sample_sheet.txt'
	sample_sheet_2_path = original_directory+'/data/normalize/'+str(experiment_id2)+'/sample_sheet.txt'

	with open(folder_path+'/sample_sheet.txt','w') as sample_sheet:
		with open(sample_sheet_1_path) as sample_sheet_1:
			for single_line in sample_sheet_1:
				sample_sheet.write(single_line)
		with open(sample_sheet_2_path) as sample_sheet_2:
			sample_sheet_2.readline()
			for single_line in sample_sheet_2:
				sample_sheet.write(single_line)
	sample_sheet_path = folder_path+'/sample_sheet.txt'	
	html_body = 'This is a confirmation message that your combined studies for experiment '+str(experiment_id1)+' and '+str(experiment_id2) +' has been scheduled. The id for your experiment is '+str(experiment_id)+'. A confirmation email has been sent out to '+str(user_info_dict['user_email'])
	output_name = str(experiment_id)+'.zip'
	url_link = ip+'/static/data/normalize/'+str(experiment_id)+'/'+output_name
	html_destination_folder = original_directory+'/static/data/normalize/'+str(experiment_id)+'/'
	os.makedirs(html_destination_folder)
	email_body = 'Dear '+ str(user_info_dict['user_name'])+'<br> This is a confirmation message that your combined studies for experiment '+str(experiment_id1)+' and '+str(experiment_id2) +' has finsihed. The id for your experiment is '+str(experiment_id)+'.You can access the output here: <br>'+ url_link+'<br>Sincerely,<br>RnaSeqPipeline Notifier'
	def cuff_norm_thread(mouse_gtf,sample_sheet_path,folder_path,experiment_id1,experiment_id2,email_body,html_destination_folder,user_info_dict):
		#mouse_gtf = thread_arg[0]
		#sample_sheet_path = thread_arg[1]
		#folder_path = thread_arg[2]
		#experiment_id1 = thread_arg[3]
		#experiment_id2 = thread_arg[4]
		#email_body = thread_arg[5]		
		
		subprocess.Popen(['cuffnorm','-o','cnout','-p','8','--use-sample-sheet',mouse_gtf,sample_sheet_path],cwd=folder_path).wait()
		output_name = str(experiment_id)+'.zip'
		cuffnorm_folder = folder_path+'/cnout' 
		subprocess.Popen(['zip','-r',output_name,cuffnorm_folder],cwd=folder_path).wait()
		compressed_output = folder_path+'/'+output_name		
		shutil.copy(compressed_output,html_destination_folder)
		#email_body = 'Dear '+ str(user_info_dict['user_name'])+'<br> This is a confirmation message that your combined studies for experiment '+str(experiment_id1)+' and '+str(experiment_id2) +' has finsihed. The id for your experiment is '+str(experiment_id)+'.You can access the output here: <br>'+ url_link+'<br>Sincerely,<br>RnaSeqPipeline Notifier'
		send_email(user_info_dict['user_email'],'RnaSeqPipeline@rutgers.edu','Finished Analysis for '+str(experiment_id1)+' and '+str(experiment_id2),email_body)
	single_thread = Thread(target=cuff_norm_thread,args=(mouse_gtf,sample_sheet_path,folder_path,experiment_id1,experiment_id2,email_body,html_destination_folder,user_info_dict))
	single_thread.start()
	return render_template('success.html',success_text=html_body)
@app.route('/analyze/decision_tree_id',methods=['GET'])
def get_info_decision_tree_id():
	return render_template('input_data_experiment_id.html',function_name='get_info_decision_tree')
@app.route('/analyze/decision_tree_id',methods=['POST'])
def get_info_decision_tree():
	experiment_id = request.form['experiment_id']
	folder_path = original_directory+'/data/normalize/'+str(experiment_id)+'/cnout'
	script_path = original_directory+'/RScripts/before_decision_tree.r'
	if os.path.isdir(folder_path) == False:
		return render_template('error.html',error_text='The experiment id is invalid or did not finish yet')
	if not os.path.exists(folder_path+'/post_quality_control_data.rds'):
		return render_template('error.html',error_text='The quality control dataset does not exist for this experiment. Please run the quality control program first')
	#os.chdir(folder_path)
	#Rscript ~/RNASeqPipeline/RScripts/get_pheno_data.r
	subprocess.Popen(['Rscript',script_path],cwd=folder_path).wait()
	output_text = folder_path+'/before_decision_tree_pData_table.txt'
	html_table = convert_file_to_html_table(output_text)
	return render_template('input_data_decision_tree.html',html_table=html_table,experiment_id=experiment_id)
@app.route('/analyze/decision_tree',methods=['POST'])
def get_decision_tree():
	experiment_id = request.form['experiment_id']
	folder_path = original_directory+'/data/normalize/'+str(experiment_id)+'/cnout'
	all_groups = []
	#for single_key in request.form:
	group_done = False	
	current_group_num = 1
	while group_done != True:
		new_group_id = 'group_'+str(current_group_num)
		if new_group_id in request.form:
			group_list = parse_input_str(request.form[new_group_id])
			if isinstance(group_list,basestring):
				return render_template('error.html',error_text=group_list)
			all_groups.append(group_list)
			current_group_num = current_group_num + 1
		else:
			group_done = True

	gene_fkpm_file =  original_directory+'/data/normalize/'+str(experiment_id)+'/cnout/before_decision_tree_exprs_table.txt'
	genes_dict = {}
	output_text = folder_path+'/before_decision_tree_pData_table.txt'
	class_names = []
	feature_names = []
	y_values = []
	x_values = []
	group_1_feature = []
	group_2_feature = []
	combined_locations = []
	with open(output_text) as table_file:
		table_file.readline()
		counter = 1
		for single_line in table_file:
			group_counter = 0
			while group_counter < len(all_groups):				
				if counter in all_groups[group_counter]:
					group_label = group_counter + 1
					y_values.append(group_label)				
					combined_locations.append(counter)
					break
				group_counter = group_counter + 1				
			counter = counter + 1
	all_group_counter = 0
	while all_group_counter < len(all_groups):
		group_label_str = 'group_'+str(all_group_counter+1)+'_name'
		class_names.append(request.form[group_label_str])
		all_group_counter = all_group_counter + 1
	with open(gene_fkpm_file) as fpkm_file:
		header_line = fpkm_file.readline()
		for single_line in fpkm_file:
			line_split = single_line.split()
			sample_value_list = []
			for single_location in combined_locations:
				if single_location >= len(line_split):
					sample_value_list.append(0)
				else:
					sample_value_list.append(float(line_split[single_location]))
			genes_dict[line_split[0]] = sample_value_list
			feature_names.append(line_split[0])


	class_counter = 0
	while class_counter < len(combined_locations):
		feature_data = []
		feature_counter = 0
		while feature_counter < len(feature_names):
			feature_data.append(genes_dict[feature_names[feature_counter]][class_counter])
			feature_counter = feature_counter + 1
		x_values.append(feature_data)
		class_counter = class_counter + 1
	classifier = tree.DecisionTreeClassifier()
	classifier = classifier.fit(x_values,y_values)
	with open(folder_path+'/graph.dot', 'w') as graph_file:
		graph_file = tree.export_graphviz(classifier, out_file=graph_file,feature_names=feature_names,
			class_names=class_names,filled=True,rounded=True,special_characters=True)
	output_figure = folder_path+'/graph.png'
	figure_destination_folder = original_directory+'/static/data/normalize/'+str(experiment_id)+'/'
	subprocess.Popen(['dot','-Tpng','-Gdpi=600','graph.dot','-o','graph.png'],cwd=folder_path).wait()
	shutil.copy(output_figure,figure_destination_folder)
	figure_link = '/static/data/normalize/'+str(experiment_id)+'/graph.png'		
	return render_template('show_figure_no_link.html',image_link=figure_link)

@app.route('/diff',methods=['GET'])
def get_input_diff_data():
	return render_template('input_diff_data.html')
@app.route('/diff',methods=['POST'])
def get_diff_experiment():
	#original_directory = os.getcwd()
	found_experiment_id = False
	condition_dict = {}
	#Get expereminet Id
	while found_experiment_id == False:
		experiment_id = randint(10000,99999)
		folder_path = original_directory+'/data/diff/'+str(experiment_id)
		if os.path.isdir(folder_path):
			continue
		else:
			found_experiment_id = True
	#move into the experiment directory
	os.makedirs(folder_path)
	#os.chdir(folder_path)
	#handle urls and condition names
	for single_key in request.form:
		split_str = single_key.split('_')
		if 'name' in single_key:
			if 'user' not in single_key:
				condition_dict[split_str[1]] = request.form[single_key]
		else:
			if 'user' not in single_key:

				sample_path = folder_path +'/condition_'+split_str[1]+'/sample_'+split_str[3]				
				sample_url = request.form[single_key]
				if '://' not in sample_url:
					correct_url = 'http://'+sample_url
				else:
					correct_url = sample_url.replace('ftp://','http://')
				downloading_mutex.acquire()				
				try:
					os.makedirs(sample_path)
					os.chdir(sample_path)
					print correct_url
					split_url = correct_url.split('/')
					response = requests.get(correct_url, stream=True)
					print response
					#print response.text
					if response.encoding == 'utf-8' or response.status_code >= 400:
						print response.encoding
						print response.status_code
						error_response = "The Url: " + correct_url + " for "+single_key+" is not valid."
						os.chdir(original_directory)
						shutil.rmtree(folder_path)
						return render_template('error.html',error_text=error_response)

					with open(split_url[-1],'wb') as sample_file:
						shutil.copyfileobj(response.raw,sample_file)
					del response
					print "downloaded file"
					time.sleep(1.5)
				except:
					error_response = "The Url: " + correct_url + " for "+single_key+" is not valid."
					print sys.exc_info()
					os.chdir(original_directory)
					shutil.rmtree(folder_path)
					return render_template('error.html',error_text=error_response)
				finally:
					downloading_mutex.release()
	#os.chdir(folder_path)

	

	#sort the conditions by number
	#sorted_condition_tuple = sorted(condition_dict.items(), key=operator.itemgetter(1))
	#condition_list = []
	#full_condition_list = 'Condition Name\n'
	#for single_tuple in sorted_condition_tuple:
	#	condition_element = ' '.join(map(str,single_tuple))
	#	condition_list.append(condition_element)
	#full_condition_list = '\n'.join(condition_list)
	#print full_condition_list
	#save condition names into a file
	
	form_files = request.files
	for single_file_key in form_files:
		split_str = single_file_key.split('_')
		sample_path = folder_path +'/condition_'+split_str[1]+'/sample_'+split_str[3]
		downloading_mutex.acquire()
		try:
			os.makedirs(sample_path)
			os.chdir(sample_path)		
			single_file = form_files[single_file_key]
			if '.sra' not in single_file.filename:
				error_response = "The file: " + single_file.filename + " for "+single_file_key+" is not a valid sra file."
				os.chdir(original_directory)
				shutil.rmtree(folder_path)
				return render_template('error.html',error_text=error_response)
			single_file.save(secure_filename(single_file.filename))
		except:
			print sys.exc_info()
			os.chdir(original_directory)
			shutil.rmtree(folder_path)
			return render_template('error.html',error_text='There was an error processing your files, please check the server logs')
		finally:
			downloading_mutex.release()


	#os.chdir(folder_path)
	for condition_num in condition_dict:
		condition_path = folder_path+'/condition_'+str(condition_num)
		if os.path.isdir(condition_path) == False:
			error_response = "The condition: " + condition_dict[condition_num] + " is missing a sample."
			os.chdir(original_directory)
			shutil.rmtree(folder_path)
			return render_template('error.html',error_text=error_response)	
	#os.chdir(original_directory+'/data/upload')
	#print os.getcwd()
	user_info_dict = {}
	user_info_dict['user_name'] = request.form['user_name']
	user_info_dict['user_email'] = request.form['user_email']

	with open(folder_path+'/condition_names.json','w') as condition_names:
		json.dump(condition_dict,condition_names)
	with open(folder_path+'/user_info.json','w') as user_info:
		json.dump(user_info_dict,user_info)
	
	#os.chdir(original_directory)
	client = MongoClient('mongodb://localhost:27017/')
	experiment_db = client.experiment_database
	diff_collection =experiment_db.diff_collection
	experiment_queue = diff_collection.find_one({'name':'experiment_queue'})
	if experiment_queue == None:
		new_queue = []
		new_queue.append(experiment_id)
		new_queue_dict = {'name':'experiment_queue','data':new_queue}
		diff_collection.insert_one(new_queue_dict)
	else:
		queue = experiment_queue['data']
		queue.append(experiment_id)		
		experiment_queue['data'] = queue
		diff_collection.replace_one({'name':'experiment_queue'},experiment_queue)

	os.chdir(original_directory)

	email_body = 'Dear '+ user_info_dict['user_name']+'<br> This is a confirmation message that your experiment has been scheduled. The id for your experiment is ' + str(experiment_id)+'<br>Sincerely,<br>RnaSeqPipeline Notifier'
	send_email(user_info_dict['user_email'],'RnaSeqPipeline@rutgers.edu','Differential Experiment Scheduled ID: '+str(experiment_id),email_body)
	html_body = 'This is a confirmation message that your experiment has been scheduled. The id for your experiment is ' + str(experiment_id) +'. A confirmation email has been sent out to '+user_info_dict['user_email']
	return render_template('success.html',success_text=html_body)

@app.route('/analyze/manual_classification_id',methods=['GET'])
def get_info_manual_classification_id():
	return render_template('input_data_experiment_id.html',function_name='get_info_manual_classification')
@app.route('/analyze/manual_classification_id',methods=['POST'])
def get_info_manual_classification():
	experiment_id = request.form['experiment_id']
	folder_path = original_directory+'/data/normalize/'+str(experiment_id)+'/cnout'
	script_path = original_directory+'/RScripts/get_current_data.r'
	if os.path.isdir(folder_path) == False:
		return render_template('error.html',error_text='The experiment id is invalid or did not finish yet')
	if not os.path.exists(folder_path+'/post_quality_control_data.rds'):
		return render_template('error.html',error_text='The quality control dataset does not exist for this experiment. Please run the quality control program first')
	#os.chdir(folder_path)	
	#Rscript ~/RNASeqPipeline/RScripts/get_current_data.r rds_file table_file
	subprocess.Popen(['Rscript',script_path,'post_quality_control_data.rds','manual_classification_table_before.txt'],cwd=folder_path).wait()
	output_text = folder_path+'/manual_classification_table_before.txt'
	html_table = convert_file_to_html_table(output_text)
	return render_template('input_data_manual_classification.html',html_table=html_table,experiment_id=experiment_id)	
@app.route('/analyze/manual_classification',methods=['POST'])
def get_manual_classification():
	experiment_id = request.form['experiment_id']
	folder_path = original_directory+'/data/normalize/'+str(experiment_id)+'/cnout'
	if os.path.isdir(folder_path) == False:
		return render_template('error.html',error_text='The experiment id is invalid or did not finish yet')
	if not os.path.exists(folder_path+'/post_quality_control_data.rds'):
		return render_template('error.html',error_text='The quality control dataset does not exist for this experiment. Please run the quality control program first')
	name_dict = {}
	num_dict = {}
	for single_key in request.form:
		if 'group' in single_key:
			group_num = single_key.split('_')[1]
			if 'name' in single_key:				
				name_dict[group_num] = request.form[single_key]
			else:
				group_range = request.form[single_key]
				group_list = parse_input_str(group_range)
				if isinstance(group_list,basestring):
					return render_template('error.html',error_text=group_list)
				num_dict[group_num] = group_list				
	output_text = folder_path+'/manual_classification_table_before.txt'
	current_cell = 1
	label_list = []
	with open(output_text) as sample_file:
		sample_file.readline()
		for single_line in sample_file:
			label = ''
			for single_key in num_dict:
				if current_cell in num_dict[single_key]:
					#print current_cell
					#print num_dict[single_key]					
					label = name_dict[single_key]
			if label == '':
				return render_template('error.html',error_text='The cell number '+srre(current_cell)+' is not included in this range. All cells must be included')
			label_list.append(label)
			#print label_list
			#time.sleep(2)
			current_cell = current_cell + 1
	script_path = original_directory+'/RScripts/manual_classification.r'	
	label_str = ','.join(map(str,label_list))
	#Rscript ~/RNASeqPipeline/RScripts/manual_classification.r label_list	
	subprocess.Popen(['Rscript',script_path,label_str],cwd=folder_path).wait()
	output_text = folder_path+'/manual_classification_table_after.txt'
	html_table = convert_file_to_html_table(output_text)
	output_figure = folder_path+'/cell_classify_plot.png'
	output_figure_tiff = folder_path+'/cell_classify_plot.tiff'
	figure_destination_folder = original_directory+'/static/data/normalize/'+str(experiment_id)+'/'	
	shutil.copy(output_figure,figure_destination_folder)
	shutil.copy(output_figure_tiff,figure_destination_folder)
	figure_link = '/static/data/normalize/'+str(experiment_id)+'/cell_classify_plot.png'
	return render_template('show_figure_and_samples.html',image_link=figure_link,html_table=html_table)
@app.route('/analyze/pseudotime_cluster_genes',methods=['GET'])
def get_info_pseudotime_cluster_genes():
	return render_template('input_data_pseudotime_cluster_genes.html')
@app.route('/analyze/pseudotime_cluster_genes',methods=['POST'])
def get_pseudotime_cluster_genes():
	experiment_id = request.form['experiment_id']
	folder_path = original_directory+'/data/normalize/'+str(experiment_id)+'/cnout'
	script_path = original_directory+'/RScripts/cell_classified_pseudotime_genes.r'
	if os.path.isdir(folder_path) == False:
		return render_template('error.html',error_text='The experiment id is invalid or did not finish yet')
	if not os.path.exists(folder_path+'/classified_cells.rds'):
		return render_template('error.html',error_text='The classified dataset does not exist for this experiment. Please run the classification program first')
	#os.chdir(folder_path)	
	#Rscript ~/RNASeqPipeline/RScripts/get_current_data.r rds_file table_file
	subprocess.Popen(['Rscript',script_path,request.form['fdr'],request.form['num_clusters']],cwd=folder_path).wait()
	output_figure = folder_path+'/cell_classified_heatmap_plot.png'
	output_figure_tiff = folder_path+'/cell_classified_heatmap_plot.tiff'
	figure_destination_folder = original_directory+'/static/data/normalize/'+str(experiment_id)+'/'
	shutil.copy(output_figure,figure_destination_folder)
	shutil.copy(output_figure_tiff,figure_destination_folder)
	figure_link = '/static/data/normalize/'+str(experiment_id)+'/cell_classified_heatmap_plot.png'
	#os.chdir(original_directory)	
	return render_template('show_figure.html',image_link=figure_link)
@app.route('/analyze/differential_heatmap',methods=["GET"])
def get_info_differential_heatmap():
	return render_template('input_data_differential_heatmap.html')
@app.route('/analyze/differential_heatmap',methods=["POST"])
def get_differential_heatmap():
	experiment_id = request.form['experiment_id']
	gini_cutoff = float(request.form['gini_cutoff'])
	folder_path = original_directory+'/data/normalize/'+str(experiment_id)+'/cnout'
	script_path = original_directory+'/RScripts/cell_classified_list.r'	
	if os.path.isdir(folder_path) == False:
		return render_template('error.html',error_text='The experiment id is invalid or did not finish yet')
	if not os.path.exists(folder_path+'/classified_cells.rds'):
		return render_template('error.html',error_text='The classified dataset does not exist for this experiment. Please run the classification program first')
	subprocess.Popen(['Rscript',script_path],cwd=folder_path).wait()
	gene_fkpm_file =  original_directory+'/data/normalize/'+str(experiment_id)+'/cnout/cell_exprs_list.txt'
	genes_dict = {}
	output_text = folder_path+'/before_decision_tree_pData_table.txt'
	group_counter = 1
	group_dict = {}
	class_names = []
	y_values = []
	combined_locations = []
	gene_list = []
	gene_class = []
	with open(folder_path+'/cell_type_list.txt') as cell_type_file:
		counter = 1
		for single_line in cell_type_file:
			if single_line not in group_dict:
				group_dict[single_line] = group_counter
				class_names.append(single_line)
				group_counter = group_counter + 1
			y_values.append(group_dict[single_line])
			combined_locations.append(counter)
			counter = counter + 1		

	
	feature_names = []
	group_1_feature = []
	group_2_feature = []
	
	with open(gene_fkpm_file) as fpkm_file:
		header_line = fpkm_file.readline()
		for single_line in fpkm_file:
			line_split = single_line.split()
			sample_value_list = []
			for single_location in combined_locations:
				if single_location >= len(line_split):
					sample_value_list.append(0)
				else:
					sample_value_list.append(float(line_split[single_location]))
			genes_dict[line_split[0]] = sample_value_list
			feature_names.append(line_split[0])

	
	
	while len(gene_list) < int(request.form['num_genes']):
		class_counter = 0
		x_values = []
		while class_counter < len(combined_locations):
			feature_data = []
			feature_counter = 0
			while feature_counter < len(feature_names):
				feature_data.append(genes_dict[feature_names[feature_counter]][class_counter])
				feature_counter = feature_counter + 1
			x_values.append(feature_data)
			class_counter = class_counter + 1
		classifier = tree.DecisionTreeClassifier()
		classifier = classifier.fit(x_values,y_values)		
		graph_str = tree.export_graphviz(classifier, out_file=None,feature_names=feature_names,class_names=class_names,filled=True,rounded=True,special_characters=True) 
		sig_genes_dict = parse_graph_data(graph_str,gini_cutoff)
		for single_gene in sig_genes_dict:
			feature_names.remove(single_gene)
			gene_list.append(single_gene)
			gene_class.append(sig_genes_dict[single_gene])
			#print len(gene_list)
	gene_list_str = ','.join(map(str,gene_list))
	gene_class_str = ','.join(map(str,gene_class))
	script_path = original_directory+'/RScripts/cell_classified_differential.r'
	subprocess.Popen(['Rscript',script_path,gene_list_str,gene_class_str],cwd=folder_path).wait()
	output_figure = folder_path+'/cell_classified_heatmap.png'
	figure_destination_folder = original_directory+'/static/data/normalize/'+str(experiment_id)+'/'
	shutil.copy(output_figure,figure_destination_folder)
	figure_link = '/static/data/normalize/'+str(experiment_id)+'/cell_classified_heatmap.png'
	return render_template('show_figure_no_link.html',image_link=figure_link)
@app.route('/analyze/manual_differential_heatmap_id',methods=['GET'])
def get_info_manual_differential_heatmap_id():
	return render_template('input_data_experiment_id.html',function_name='get_info_manual_differential_heatmap')
@app.route('/analyze/manual_differntial_heatmap_id',methods=['POST'])
def get_info_manual_differential_heatmap():
	experiment_id = request.form['experiment_id']
	folder_path = original_directory+'/data/normalize/'+str(experiment_id)+'/cnout'
	script_path = original_directory+'/RScripts/before_decision_heatmap.r'
	if os.path.isdir(folder_path) == False:
		return render_template('error.html',error_text='The experiment id is invalid or did not finish yet')
	if not os.path.exists(folder_path+'/post_quality_control_data.rds'):
		return render_template('error.html',error_text='The quality control dataset does not exist for this experiment. Please run the quality control program first')
	#os.chdir(folder_path)
	#Rscript ~/RNASeqPipeline/RScripts/get_pheno_data.r
	subprocess.Popen(['Rscript',script_path],cwd=folder_path).wait()
	output_text = folder_path+'/before_decision_heatmap_pData_table.txt'
	html_table = convert_file_to_html_table(output_text)
	return render_template('input_data_manual_differential_heatmap.html',html_table=html_table,experiment_id=experiment_id)
@app.route('/analyze/manual_differntial_heatmap',methods=['POST'])
def get_manual_differential_heatmap():
	#Get User defined values
	experiment_id = request.form['experiment_id']
	gini_cutoff = float(request.form['gini_cutoff'])
	folder_path = original_directory+'/data/normalize/'+str(experiment_id)+'/cnout'
	all_groups = []
	#Get ranges of cells to analyze
	group_done = False	
	current_group_num = 1
	while group_done != True:
		new_group_id = 'group_'+str(current_group_num)
		if new_group_id in request.form:
			group_list = parse_input_str(request.form[new_group_id])
			if isinstance(group_list,basestring):
				return render_template('error.html',error_text=group_list)
			all_groups.append(group_list)
			current_group_num = current_group_num + 1
		else:
			group_done = True
	#Get gene features of post-quality control data
	gene_fkpm_file =  original_directory+'/data/normalize/'+str(experiment_id)+'/cnout/before_decision_heatmap_exprs_table.txt'
	genes_dict = {}
	#Folder containns all the cells in the post-quality control data
	output_text = folder_path+'/before_decision_heatmap_pData_table.txt'
	class_names = []
	feature_names = []
	y_values = []
	x_values = []
	group_1_feature = []
	group_2_feature = []
	combined_locations = []
	combined_labels = []
	gene_list = []
	gene_class = []
	with open(output_text) as table_file:
		table_file.readline()
		counter = 1
		for single_line in table_file:
			group_counter = 0
			while group_counter < len(all_groups):				
				if counter in all_groups[group_counter]:
					group_label = group_counter + 1
					y_values.append(group_label)
					combined_labels.append(request.form['group_'+str(group_counter+1)+'_name'])				
					combined_locations.append(counter)
					break
				group_counter = group_counter + 1				
			counter = counter + 1
	all_group_counter = 0
	while all_group_counter < len(all_groups):
		group_label_str = 'group_'+str(all_group_counter+1)+'_name'
		class_names.append(request.form[group_label_str])
		all_group_counter = all_group_counter + 1
	with open(gene_fkpm_file) as fpkm_file:
		header_line = fpkm_file.readline()
		for single_line in fpkm_file:
			line_split = single_line.split()
			sample_value_list = []
			for single_location in combined_locations:
				if single_location >= len(line_split):
					sample_value_list.append(0)
				else:
					sample_value_list.append(float(line_split[single_location]))
			genes_dict[line_split[0]] = sample_value_list
			feature_names.append(line_split[0])

	while len(gene_list) < int(request.form['num_genes']):
		class_counter = 0
		x_values = []
		while class_counter < len(combined_locations):
			feature_data = []
			feature_counter = 0
			while feature_counter < len(feature_names):
				feature_data.append(genes_dict[feature_names[feature_counter]][class_counter])
				feature_counter = feature_counter + 1
			x_values.append(feature_data)
			class_counter = class_counter + 1
		classifier = tree.DecisionTreeClassifier()
		classifier = classifier.fit(x_values,y_values)		
		graph_str = tree.export_graphviz(classifier, out_file=None,feature_names=feature_names,class_names=class_names,filled=True,rounded=True,special_characters=True) 
		sig_genes_dict = parse_graph_data(graph_str,gini_cutoff)
		for single_gene in sig_genes_dict:
			#Remove gene from training data
			feature_names.remove(single_gene)
			gene_list.append(single_gene)
			gene_class.append(sig_genes_dict[single_gene])			
	gene_list_str = ','.join(map(str,gene_list))
	gene_class_str = ','.join(map(str,gene_class))
	combined_list_str = ','.join(map(str,combined_locations))
	combined_class_str = ','.join(map(str,combined_labels))
	script_path = original_directory+'/RScripts/cell_manual_differential.r'
	subprocess.Popen(['Rscript',script_path,gene_list_str,gene_class_str,combined_list_str,combined_class_str],cwd=folder_path).wait()
	output_figure = folder_path+'/cell_manual_heatmap.png'
	figure_destination_folder = original_directory+'/static/data/normalize/'+str(experiment_id)+'/'
	shutil.copy(output_figure,figure_destination_folder)
	figure_link = '/static/data/normalize/'+str(experiment_id)+'/cell_manual_heatmap.png'
	return render_template('show_figure_no_link.html',image_link=figure_link)

@app.route('/analyze/diff/<diff_type>',methods=['GET'])
def get_info_diff_type(diff_type=None):
	title = diff_type.replace('_',' ')
	if diff_type == 'Get_Significant_Genes':
		return render_template('input_data_significant_gene_all_samples.html',title=title,diff_type=diff_type)
	if diff_type == 'Get_Gene_Comparison':
		return render_template('input_data_gene.html',title=title,diff_type=diff_type)
	if diff_type == 'Get_Similar_Genes':
		return render_template('input_data_similar_genes.html',title=title,diff_type=diff_type)
	if diff_type == 'Get_K_Means_Cluster':
		return render_template('input_data_cluster_num.html',title=title,diff_type=diff_type)
	return render_template('input_data_diff.html',title=title,diff_type=diff_type)
@app.route('/analyze/diff/<diff_type>',methods=['POST'])
def get_diff_type(diff_type=None):
	#List of possible values for diff_type
	#Create_CuffSet_Database
	#FPKM_Quality_Control
	#Create_Dendogram
	#Get_Significant_Genes
	#Get_Significant_Genes_Comparison
	#Get_Heatmap
	#Get_Gene_Comparison
	#Get_Similar_Genes
	#Get_K_Means_Cluster
	experiment_id = request.form['experiment_id']
	folder_path = original_directory+'/data/diff/'+str(experiment_id)+'/cdout'
	script_path = original_directory+'/RScripts/'+str(diff_type)+'.r'
	if os.path.isdir(folder_path) == False:
		return render_template('error.html',error_text='The experiment id is invalid or did not finish yet')

	if diff_type == 'Get_Significant_Genes_Comparison':
		script_path = original_directory+'/RScripts/Get_Sample_List.r'
		output_text = folder_path+'/sample_list.txt'
		subprocess.Popen(['Rscript',script_path],cwd=folder_path).wait()
		html_table = convert_file_to_html_table(output_text)
		title = diff_type.replace('_',' ')		
		return render_template('input_data_significant_gene_comparison.html',experiment_id=experiment_id,title=title,diff_type=diff_type+'1',html_table=html_table)
	if diff_type == 'Get_Significant_Genes_Comparison1':
		script_path = original_directory+'/RScripts/Get_Significant_Genes_Comparison.r'
		output_path = folder_path+'/number_of_sig_genes.Rout'
		error_file_name = diff_type+'_error.Rout'
		subprocess.Popen(['Rscript',script_path,error_file_name,request.form['first_sample'],request.form['second_sample'],request.form['alpha']],cwd=folder_path).wait()
		if os.path.exists(folder_path+'/'+error_file_name):
			error_text = "<p>"
			with open(folder_path+'/'+error_file_name) as error_file:
				for single_line in error_file:
					error_text= error_text + single_line + '<br>'
			error_text = error_text+'</p>'
			if 'Execution halted' in error_text:
				return render_template('error.html',error_text=error_text)
		with open(output_path) as output_text:
			output_str = output_text.readline()
		return render_template('success.html',success_text='The number of genes chosen is '+output_str)
	if diff_type == 'Get_Significant_Genes':
		script_path = original_directory+'/RScripts/Get_Significant_Genes.r'
		output_path = folder_path+'/number_of_sig_genes.Rout'
		error_file_name = diff_type+'_error.Rout'
		subprocess.Popen(['Rscript',script_path,error_file_name,request.form['alpha']],cwd=folder_path).wait()
		if os.path.exists(folder_path+'/'+error_file_name):
			error_text = "<p>"
			with open(folder_path+'/'+error_file_name) as error_file:
				for single_line in error_file:
					error_text= error_text + single_line + '<br>'
			error_text = error_text+'</p>'
			if 'Execution halted' in error_text:
				return render_template('error.html',error_text=error_text)
		with open(output_path) as output_text:
			output_str = output_text.readline()
		return render_template('success.html',success_text='The number of genes chosen is '+output_str)


	error_file_name = diff_type+'_error.Rout'
	figure_name = diff_type+'.png'
	if diff_type == 'Get_Gene_Comparison':
		subprocess.Popen(['Rscript',script_path,error_file_name,figure_name,request.form['gene_name']],cwd=folder_path).wait()
	elif diff_type == 'Get_Similar_Genes':
		subprocess.Popen(['Rscript',script_path,error_file_name,figure_name,request.form['gene_name'],request.form['number_of_genes']],cwd=folder_path).wait()
	elif diff_type == 'Get_K_Means_Cluster':
		subprocess.Popen(['Rscript',script_path,error_file_name,figure_name,request.form['cluster_num']],cwd=folder_path).wait()
	else:
		subprocess.Popen(['Rscript',script_path,error_file_name,figure_name],cwd=folder_path).wait()
	if os.path.exists(folder_path+'/'+error_file_name):
		error_text = "<p>"
		with open(folder_path+'/'+error_file_name) as error_file:
			for single_line in error_file:
				error_text= error_text + single_line + '<br>'
		error_text = error_text+'</p>'
		if 'Execution halted' in error_text:
			return render_template('error.html',error_text=error_text)

	if diff_type == 'Create_CuffSet_Database':
		return render_template('success.html',success_text='The CuffSet Database has been created')	
	output_figure = folder_path+'/'+figure_name
	figure_destination_folder = original_directory+'/static/data/diff/'+str(experiment_id)+'/'
	shutil.copy(output_figure,figure_destination_folder)
	figure_link = '/static/data/diff/'+str(experiment_id)+'/'+figure_name
	if diff_type == 'Get_K_Means_Cluster':
		output_text = folder_path +'/k_means_cluster.txt'
		html_table = convert_file_to_html_table(output_text)
		html_table = html_table.replace('#','Gene Name')
		html_table = html_table.replace('Cluster_Num','Cluster Number')
		return render_template('show_figure_and_genes.html',image_link=figure_link,html_table=html_table)
	return render_template('show_figure_no_link.html',image_link=figure_link)
	

@app.after_request
def add_header(response):
    response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers['Cache-Control'] = 'public, max-age=0'
    return response


@app.route('/error')
def error():
	return render_template('error.html',error_text='test')

#def clean_up(daemon_program_list):
#	for single_daemon_program in daemon_program_list:
#		single_daemon_program.stop()
#	print "All daemons stopped"
R_start_monocle = '''library("monocle")
library("reshape")
library("ggplot2")
HSMM <- readRDS('post_quality_control_data.rds')\n'''	
	

if __name__ == '__main__':
	client = MongoClient('mongodb://localhost:27017/')
	experiment_db = client.experiment_database
	#experiment_db.normalize_collection.drop()
	#experiment_db.quality_collection.drop()
	experiment_information_dict = {'name':'original_directory','data':os.getcwd()}
	server_ip_dict = {'name':'server_ip','data':ip}
	experiment_db.normalize_collection.insert_one(experiment_information_dict)
	experiment_db.normalize_collection.insert_one(server_ip_dict)
	norm_collection =experiment_db.normalize_collection
	experiment_queue =norm_collection.find_one({'name':'experiment_queue'})
	new_list = []
	#experiment_db.server_status_collection.drop()
	###new_list.append('85522')
	new_list.append('69694')
	new_list.append('46186')
	if len(new_list) != 0:
		if experiment_queue == None:
			new_queue = new_list
			new_queue.append(experiment_id)
			new_queue_dict = {'name':'experiment_queue','data':new_queue}
			norm_collection.insert_one(new_queue_dict)
		else:
			queue = experiment_queue['data']
			queue = new_list
			#queue.append(experiment_id)		
			experiment_queue['data'] = queue
			norm_collection.replace_one({'name':'experiment_queue'},experiment_queue)
	


	#experiment_queue = norm_collection.find_one({'name':'experiment_queue'})
	#experiment_id = '85522'
	#new_queue = []
	#new_queue.append(experiment_id)
	#new_queue.append('69694')
	#new_queue_dict = {'name':'experiment_queue','data':new_queue}
	#norm_collection.insert_one({'name':'experiment_queue'},new_queue_dict)
	#norm_collection.drop()
	#norm_collection.insert_one(new_queue_dict)
	#experiment_queue = norm_collection.find_one({'name':'experiment_queue'})
	#print experiment_queue
	
	#else:
	#	queue = []#experiment_queue['data']
	#	queue.append(experiment_id)
	#	experiment_queue['data'] = queue
	#	norm_collection.replace_one({'name':'experiment_queue'},experiment_queue)

	#print "starting"
	#deamon_list = []		
	#experiment_handler_daemon = experiment_handler('experiment_handler.pid')
	#experiment_handler_daemon.start()
	#deamon_list.append(experiment_handler_daemon)	
	#print "All daemons started"
	#atexit.register(clean_up,deamon_list)
	#try:
	#quality_check_thread = Thread(target=process_quality_control)
	#quality_check_thread.start()		
	#except:
	#	input_event.set()
	#	raise

	#atexit.register(close_threads)
	#app.host = '0.0.0.0'
	app.run(host='0.0.0.0',debug = True)
	
