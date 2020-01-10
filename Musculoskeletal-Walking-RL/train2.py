import time
import pandas as pd
import time,datetime
import sys,os
import yaml
import argparse
import seaborn as sns
import matplotlib.pyplot as plt
from multiprocessing import Process
from hbp_nrp_virtual_coach.virtual_coach import VirtualCoach

#TODO 1. actibelt logging tf   2.eval   3. remove nrp panel

def sim_start(experiment,server,config_file_path,results_save_path):
	global vc	
	sim = vc.launch_experiment(experiment)
	print "Configuring..."

	#load configurations from .yaml file into a python dictionary
	config = yaml.load(open(config_file_path))
	filename = config_file_path.split("/")[-1]
	config['NAME'] = filename[:-5]

	time_stamp = str(datetime.date.today())+"-"+time.strftime("%H-%M")
	WeightsPATH = config.get('DDPG_Agent',{}).get('weights_sav_path',"~/.opt/weights")
	f = open(os.path.expanduser(WeightsPATH+"/"+time_stamp+"__init__"+filename),'w')
	yaml.dump(config,f)

	tf_environment = sim.get_transfer_function('environment').splitlines()
	tf_ddpg = sim.get_transfer_function('init_DRLagent').splitlines()
	tf_controller = sim.get_transfer_function('controller').splitlines()
	tf_history = sim.get_transfer_function('history_recorder').splitlines()

	#Substritue the first line of the transfer function with the configuration dict..
	tf_environment[0] = "CONFIGURATION = " + str(config)
	tf_ddpg[0] = "CONFIGURATION = " + str(config)
	tf_controller[0] = "CONFIGURATION = " + str(config)
	tf_history[0] = "CONFIGURATION = " + str(config)

	tf_environment = "\n".join(tf_environment)
	tf_ddpg = "\n".join(tf_ddpg)
	tf_controller = "\n".join(tf_controller)
	tf_history = "\n".join(tf_history)

	sim.edit_transfer_function('environment',tf_environment)
	sim.edit_transfer_function('init_DRLagent',tf_ddpg)
	sim.edit_transfer_function('controller',tf_controller)
	sim.edit_transfer_function('history_recorder',tf_history)
	
	MAX_EP = config.get('Training',{}).get('Max_Epoch',300)
	sim.start()
	time.sleep(5)
	#wait until that csv file is created.
	ep_idx = 0
	hist_file_name = "history_" + config.get('NAME','default') + ".csv"
	while(ep_idx <= MAX_EP):
	#terminate the simulation when it reaches maximum epochs.
		time.sleep(0.25)
		#retrive current states from csv file
		csv_curr_stat = sim.get_last_run_csv_file(hist_file_name)
		lst_line = csv_curr_stat.splitlines()[-1].split(',') #last line of the csv, namely the newest states.
		if lst_line[0] != "Epoch": #avoiding the case that the csv file contains only the header.
			print lst_line
			ep_idx = int(lst_line[0])
			#height = float(lst_line[1])
			#reward = float(lst_line[2])

	sim.stop()


def main(experiment,config_path,results_save_path,environment,storage_username,storage_password):
	vc = VirtualCoach(environment=environment, storage_username=storage_username, storage_password=storage_password)
	global vc
	vc.print_cloned_experiments()

	#retrive the list of availiable servers
	servers = vc.print_available_servers()
	if servers[0] == "No available servers.":
		print "No available server, exit."
		sys.exit()
	else:
		print len(servers)," server(s) available."
		flag_occupied = [False]*len(servers)

	#list of configuration files 
	configurations = os.listdir(config_path)
	configurations = list(filter(lambda x: x.endswith('yaml'), configurations)) #only yaml file should be in the list

	while True:
		if len(configurations) > 0:
		#check whether there is configuration not being simulated yet.
			if len(servers) > 0:
			#allocate an availiable server to the simulation, if no server is available, just wait. 
				curr_config_path = config_path + "/" + configurations.pop()
				print curr_config_path

				server = servers.pop()

				#sim_start(experiment,server,curr_config_path,results_save_path)
				#create a new process to run the simulation
				p = Process(target=sim_start, args=(experiment,server,curr_config_path,results_save_path))
				p.start()
			else:
				print len(configurations)," configurations in queue. Waiting for available server"
				while vc.print_available_servers()[0] == "No available servers.":
					time.sleep(1)
				servers = vc.print_available_servers()
		else:
			break
	p.join()
	print "Training Complete!"
	#evaluate(results_save_path)


#----------------------------------------------------------------------#
parser = argparse.ArgumentParser(description='Parallel training script.')
parser.add_argument('--experiment','-x',help='name of the experiment to be launched. default: Neurorobotics-Musculoskeletal-Walking-Robot-DRL_0', default='Neurorobotics-Musculoskeletal-Walking-Robot-DRL_0')
parser.add_argument('--config_path','-c',help='path to configuration files. default: ./simulation_config',default='./simulation_config')
parser.add_argument('--results_path','-r',help='path to simulatuion results. default: ./results', default='./results')
parser.add_argument('--environment','-e',help='environment of NRP backend. default: local', default='local')
parser.add_argument('--storage_username','-n',help='NRP storage user name. default: nrpuser', default='nrpuser')
parser.add_argument('--storage_password','-p',help='NRP storage password. default: password', default='password')
args = parser.parse_args()

if __name__ == "__main__":
	if args.config_path[-1] == '/':
		args.config_path = args.config_path[:,-1]
	main(args.experiment,args.config_path,args.results_path,args.environment,args.storage_username,args.storage_password)
