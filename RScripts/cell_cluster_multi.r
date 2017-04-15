#Usage:
#Rscript cell_cluster_multi.r cluster_number
library("monocle")
library("reshape")
library('ggplot2')
args <- commandArgs(trailingOnly=TRUE)
if(length(args)==0)
{
	print("Usage: Rscript cell_cluster.r cluster_number cluster_labels")
}
cluster_number <- args[1]
HSMM <- readRDS('post_quality_control_data.rds')
HSMM <- clusterCells(HSMM, num_clusters=as.numeric(cluster_number))#, tol = 1e-6,max_components = 10, verbose=TRUE,param.gamma=300)
saveRDS(HSMM,'post_quality_control_data_multi.rds')
#HSMM <- readRDS('post_quality_control_data_multi.rds')
print(plot_cell_trajectory(HSMM, color="Cluster"))
ggsave("cell_cluster_plot.png")
ggsave("cell_cluster_plot.tiff", width = 7, height = 7,dpi=600)
cell_name <- pData(HSMM)$name
cluster_num <- pData(HSMM)$Cluster
write.table(cell_name,'cluster_name_multi.txt',sep="\t",quote=FALSE,row.names=FALSE,col.names=FALSE)
write.table(cluster_num,'cluster_clusternum_multi.txt',sep="\t",quote=FALSE,row.names=FALSE,col.names=FALSE)
dev.off() 