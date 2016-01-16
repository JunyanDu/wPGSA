#!/usr/bin/python
# coding: UTF-8

import sys, math, numpy
import scipy as sp
from scipy import stats
from rpy2.robjects import r
import rpy2.robjects as robjects

__version__ = "1.0.0"

def get_progressbar_str(progress):
	MAX_LEN = 30
	BAR_LEN = int(MAX_LEN * progress)
	return ('[' + '=' * BAR_LEN +
			('>' if BAR_LEN < MAX_LEN else '') +
			' ' * (MAX_LEN - BAR_LEN) +
			'] %.1f%%' % (progress * 100.))

def read_logFC(logFC_file):
	exp_value = {}
	tp_list = []
	with open(logFC_file, 'r') as fi:
		line = fi.readline()
		itemList = line[:-1].split('\t')
		for i in range(1,len(itemList)):
			tp_list.append(itemList[i])
		for tp in tp_list:
			exp_value[tp] = {}
		line = fi.readline()
		while line:
			itemList = line[:-1].split('\t')
			gene_symbol = itemList[0]
			for i in range(len(tp_list)):
				if itemList[i+1] != "NA":
					exp_value[tp_list[i]][gene_symbol] = float(itemList[i+1])
			line = fi.readline()

	return exp_value, tp_list

def read_network(network_file):
	positive = {}
	experiment = {}
	with open(network_file, 'r') as fi:
		line = fi.readline()
		line = fi.readline()
		while line:
			itemList = line[:-1].split('\t')
			TF = itemList[0]
			gene_symbol = itemList[2]
			if int(itemList[5]) >= 0:
				if TF not in positive:
					positive[TF] = {}
				positive[TF][gene_symbol] = float(itemList[4])
				if TF not in experiment:
					experiment[TF] = float(itemList[5])
			line = fi.readline()

	return positive, experiment

def wPGSA(tp_list,exp_value,positive,experiment):
	result = {}
	result["p_value"] = {}
	result["q_value"] = {}
	result["z_score"] = {}

	x = 1.0
	total_num = len(tp_list) * len(experiment)

	for tp in tp_list:
		positive_vector = {}
		experiment_vector = {}
		exp_vector = []
		for gene_symbol in exp_value[tp]:
			exp_vector.append(exp_value[tp][gene_symbol])
			for TF in experiment:
				if TF not in positive_vector:
					positive_vector[TF] = []
				if TF not in experiment_vector:
					experiment_vector[TF] = []
				experiment_vector[TF].append(experiment[TF])
				if gene_symbol in positive[TF]:
					positive_vector[TF].append(positive[TF][gene_symbol])
				else:
					positive_vector[TF].append(0.0)

		mean = numpy.mean(exp_vector)
		var = numpy.var(exp_vector)
		std = numpy.std(exp_vector)
		gene_size = len(exp_vector)

		TF_list = []

		for TF in experiment_vector:
			TF_list.append(TF)

		result["z_score"][tp] = []
		result["p_value"][tp] = []

		for TF in experiment_vector:
			value_list = []
			size = len(positive[TF])
			target_vector = numpy.array(exp_vector)*numpy.array(positive_vector[TF])/numpy.array(experiment_vector[TF])
			total_weight = sum(numpy.array(positive_vector[TF])/numpy.array(experiment_vector[TF]))
			target_mean = sum(target_vector)/total_weight
			target_var = 0
			for i in range(len(positive_vector[TF])):
				target_var += positive_vector[TF][i] * (exp_vector[i]-target_mean)**2 / experiment_vector[TF][i]
			target_var = target_var / total_weight
			target_std = numpy.sqrt(target_var)

			SE = numpy.sqrt(var/size+target_var/size)
			df = (size - 1) * (var + target_var)**2 / (var**2 + target_var**2)

			z_score = (target_mean - mean) / SE
			result["z_score"][tp].append(z_score)
			p_value = sp.stats.t.sf(abs(z_score),df)
			result["p_value"][tp].append(p_value)

			progress = x / total_num
			sys.stderr.write('\r\033[K' + get_progressbar_str(progress))
			sys.stderr.flush()

			x += 1


		R_p_list = robjects.FloatVector(result["p_value"][tp])
		r.assign('R_p_list', R_p_list)
		r.assign('list_len', len(R_p_list))
		result["q_value"][tp] = r('p.adjust(R_p_list, method="BH", n=list_len)')

	return result,TF_list

def write_result(result,TF_list,tp_list,experiment,output):
	for data in result:
		with open(output+'_TF_wPGSA_'+data+'.txt','w') as fo:
			fo.write("TF\tNumber_of_ChIPexp\t"+data+"_mean")
			for tp in tp_list:
				fo.write("\t"+tp)
			fo.write('\n')
			for i in range(len(TF_list)):
				fo.write(TF_list[i]+'\t'+str(int(experiment[TF_list[i]])))
				if data == "z_score":
					mean = 0
					for tp in tp_list:
						mean += result[data][tp][i]
					mean = mean / len(tp_list)
				else:
					mean = 1
					for tp in tp_list:
						mean *= result[data][tp][i]
					mean = mean ** (1.0/len(tp_list))
				fo.write('\t'+str(mean))
				for tp in tp_list:
					fo.write("\t"+str(result[data][tp][i]))
				fo.write('\n')

def start():
	argvs = sys.argv
	logFC_file = argvs[1]
	network_file = argvs[2]
	exp_value, tp_list = read_logFC(logFC_file)
	positive, experiment = read_network(network_file)
	result,TF_list = wPGSA(tp_list,exp_value,positive,experiment)
	output = argvs[1].replace('.txt','')
	write_result(result,TF_list,tp_list,experiment,output)

if __name__ == "__main__":
	try:
		start()
	except KeyboardInterrupt:
		pass
	except IOError as e:
		if e.errno == errno.EPIPE:
			pass
		else:
			raise