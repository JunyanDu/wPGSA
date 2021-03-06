#!/bin/sh
#$ -S /bin/sh

project_root=$1
Genome=$2
bioproject=$3
sample_GSM=$4
control_GSM=$5
userID=`whoami`

macs2=/home/$userID/.local/bin/macs2

cd $project_root/$Genome/$bioproject/

case "$Genome" in
	mm10 | mm9 | mm8) macsg=mm;;
	hg19 | hg18) macsg=hs;;
	ce10 | ce6) macsg=ce;;
	dm3 | dm2) macsg=dm;;
	sacCer2 | sacCer3) macsg=12100000;;
esac

#echo $macsg

Logfile="$project_root/$Genome/$bioproject/$sample_GSM.macs2.log.txt"

while :; do
	is_sample_GSM=`cat $project_root/$Genome/$bioproject/$sample_GSM.log.txt|tail -n 1|grep -c "$sample_GSM finished"`
	is_control_GSM=`cat $project_root/$Genome/$bioproject/$control_GSM.log.txt|tail -n 1|grep -c "$control_GSM finished"`
	no_sample_GSM=`cat $project_root/$Genome/$bioproject/$sample_GSM.log.txt|tail -n 1|grep -c "$sample_GSM no sra file"`
	no_control_GSM=`cat $project_root/$Genome/$bioproject/$control_GSM.log.txt|tail -n 1|grep -c "$control_GSM no sra file"`
	if [ $no_sample_GSM = "1" ]; then
		break
	fi
	if [ $no_control_GSM = "1" ]; then
		break
	fi
	if [ $is_sample_GSM = "1" ]; then
		if [ $is_control_GSM = "1" ]; then
			nQ=`qstat|tail -n +3| awk '{print $5}'|cut -c1|grep -cv -e "r"`

			if [ $nQ -le 10 ]; then
				qsub -N "macs$sample_GSM" -cwd -o $Logfile -e $Logfile -pe def_slot 4 -b y $macs2 callpeak --fix-bimodal -t $project_root/$Genome/$bioproject/$sample_GSM.bam -c $project_root/$Genome/$bioproject/$control_GSM.bam -g $macsg -n $sample_GSM
				sleep 1
				break
			fi
		fi
	fi
done
exit