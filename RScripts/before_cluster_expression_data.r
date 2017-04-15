#Usage:
#Rscript before_cluster_expression_data.r
library("monocle")
library("reshape")
HSMM <- readRDS("post_quality_control_data.rds")
write.table(exprs(HSMM), 'cell_cluster_exprs_list.txt', sep="\t",quote=FALSE)