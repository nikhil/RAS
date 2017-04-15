#Usage:
#Rscript check_cluster data_file
library("monocle")
args <- commandArgs(trailingOnly=TRUE)
if(length(args)==0)
{
	print("Usage: Rscript check_cluster data_file")
}
data_file <- args[1]
HSMM <- readRDS(data_file)
if("Cluster" %in% colnames(pData(HSMM))) {
	cat("True")
} else {
	cat("False")
}