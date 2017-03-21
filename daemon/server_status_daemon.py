from daemon import Daemon
import sys
import time
import os
from pymongo import MongoClient
import psutil

project_dir = os.getcwd()[:-7]

class server_status(Daemon):

		
	def run(self):

		def add_to_fixed_length_list(fixed_length,list_element,element_to_add):
			list_element.append(element_to_add)
			while len(list_element)>fixed_length:
				list_element.pop(0)
			return list_element
		
		while True:			
			client = MongoClient('mongodb://localhost:27017/')
			experiment_db = client.experiment_database
			status_collection =experiment_db.server_status_collection
			status_database_dict = status_collection.find_one({'name':'server_status_dict'})
			first_status = False
			if status_database_dict == None:
				status_dict = {}
				status_dict['temps'] = {}
				status_dict['cpu'] = {}
				status_dict['network'] = []
				status_dict['disk'] = []
				status_dict['memory'] = []
				status_dict['load'] = []
				first_status = True
			else:
				status_dict = status_database_dict['data']
			#Temperature
			if not hasattr(psutil, "sensors_temperatures"):
				print "Platform is not supported"
			else:
				temperatures = psutil.sensors_temperatures(fahrenheit=True)
				if 'coretemp' in temperatures:
					coretemp_temps = temperatures['coretemp']
					cricital_list = []
					for single_temp_elem in coretemp_temps:
						if single_temp_elem.label not in status_dict['temps']:
							status_dict['temps'][single_temp_elem.label] = []
						status_dict['temps'][single_temp_elem.label] = add_to_fixed_length_list(24,status_dict['temps'][single_temp_elem.label],single_temp_elem.current)
						cricital_list.append(single_temp_elem.critical)
				status_dict['temps']['critical_temp'] = min(cricital_list)
			#Cpu
			cpu_freq_list = psutil.cpu_freq(percpu=True)
			cpu_count = 0
			for single_cpu_freq in cpu_freq_list:
				cpu_key = "Cpu "+ str(cpu_count)
				if cpu_key not in status_dict['cpu']:
					status_dict['cpu'][cpu_key] = []
				single_cpu_list = status_dict['cpu'][cpu_key]
				single_cpu_list = add_to_fixed_length_list(24,single_cpu_list,single_cpu_freq[0])
				status_dict['cpu'][cpu_key] = single_cpu_list
				cpu_count = cpu_count + 1



			#Network
			bytes_received = psutil.net_io_counters()[1]
			bytes_received_gbs = round(bytes_received/float(1000000),2)
			network_list = status_dict['network']
			network_list = add_to_fixed_length_list(25,network_list,bytes_received_gbs)
			#Disk
			disk_percentage = psutil.disk_usage(project_dir).percent
			disk_list = status_dict['disk']
			disk_list = add_to_fixed_length_list(24,disk_list,disk_percentage)
			#Memory
			memory_percentage = psutil.virtual_memory().percent
			memory_list = status_dict['memory']
			memory_list = add_to_fixed_length_list(24,memory_list,memory_percentage)
			#Load
			load_list = status_dict['load']
			load_avg_list = os.getloadavg()
			load_sum = 0
			for load_elem in load_avg_list:
				load_sum = load_sum + load_elem
			load_avg = round(load_sum/float(len(load_avg_list)),2)
			load_list = add_to_fixed_length_list(24,load_list,load_avg)
			status_dict['network'] = network_list
			status_dict['disk'] = disk_list
			status_dict['memory'] = memory_list
			status_dict['load'] = load_list			
			new_status_dict = {'name':'server_status_dict','data':status_dict}			
			if first_status == True:				
				status_collection.insert_one(new_status_dict)
			else:
				status_collection.replace_one({'name':'server_status_dict'},new_status_dict)



			time.sleep(60)



if __name__ == "__main__":
	daemon = server_status(os.getcwd()+'/server_status.pid',stdin='/dev/null', stdout=os.getcwd()+'/server_status_out.log', stderr=os.getcwd()+'/server_status_err.log')
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