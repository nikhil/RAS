import subprocess
import os
import re
import json
sendgrid_api_key = '[api key]'
mouse_gtf = '/home/nk371/Mouse_data/Mus_musculus/UCSC/mm10/Annotation/genes.gtf'
mouse_genome = '/home/nk371/Mouse_data/Mus_musculus/UCSC/mm10/Sequence/Bowtie2Index/genome'
folder_path = '/home/nk371/RNASeqPipeline/data/normalize/85325'
with open(folder_path+'/condition_names.json') as condition_names_data:
	condition_names = json.load(condition_names_data)
with open(folder_path+'/sample_sheet.txt','w') as sample_sheet_input:
	sample_sheet_input.write('sample_id\tgroup_label\n')
condition_folders = os.walk(folder_path).next()[1]
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
			os.chdir(sample_subdir)
			library_type = 'fr-unstranded'
			print sample_1_fastq
			print sample_2_fastq
			#if sample_2_fastq != None:
				#tophat2 -o thout1_firststrand -p 8 --library-type=fr-firststrand -G ~/Mouse_data/Mus_musculus/UCSC/mm10/Annotation/genes.gtf ~/Mouse_data/Mus_musculus/UCSC/mm10/Sequence/Bowtie2Index/genome sample1_1.fastq sample1_2.fastq
			#	subprocess.call(['tophat2','-o','thout','-p','8','--library-type',library_type,'-G',mouse_gtf,mouse_genome,sample_1_fastq,sample_2_fastq])
			#else:
			#	subprocess.call(['tophat2','-o','thout','-p','8','--library-type',library_type,'-G',mouse_gtf,mouse_genome,sample_1_fastq])
			#cuffquant--------------------------
			bam_file = os.getcwd()+'/thout/accepted_hits.bam'
			#cuffquant -o CELL_T24_A01_cuffquant_out GENCODE.gtf CELL_T24_A01_thout/accepted_hits.bam
			subprocess.call(['cuffquant','-o','qout','-p','8','--library-type',library_type,mouse_gtf,bam_file])
			condition_num = (re.search('\d+',single_condition_folder)).group()
			group_label = condition_names[str(condition_num)]
			sample_id = os.getcwd()+'/qout/abundances.cxb'
			with open(folder_path+'/sample_sheet.txt','a') as sample_sheet_input:
				sample_sheet_input.write(str(sample_id+'\t'+group_label+'\n'))
os.chdir(folder_path)
sample_sheet_path = folder_path+'/sample_sheet.txt'
subprocess.call(['cuffnorm','-o','cnout','-p','8','--library-type',library_type,'--use-sample-sheet',mouse_gtf,sample_sheet_path])