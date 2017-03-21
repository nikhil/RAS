#Usage:
#Rscript get_current_data.r rds_file table_file
library("monocle")
library("reshape")
args <- commandArgs(trailingOnly=TRUE)
if(length(args)!=2)
{
	print("Usage: Rscript get_current_data.r rds_file table_file")
}
HSMM <- readRDS(args[1])
pData(HSMM)$Size_Factor <- NULL
rownames(pData(HSMM)) <- NULL
pData(HSMM)$Total_mRNAs <- Matrix::colSums(exprs(HSMM))
write.table(pData(HSMM), args[2], sep="\t",quote=FALSE)