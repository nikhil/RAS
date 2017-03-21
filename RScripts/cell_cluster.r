#Usage:
#Rscript cell_cluster.r cluster_number
library("monocle")
library("reshape")
library('ggplot2')
args <- commandArgs(trailingOnly=TRUE)
if(length(args)==0)
{
	print("Usage: Rscript cell_cluster.r cluster_number")
}
cluster_number <- args[1]
HSMM <- readRDS('post_quality_control_data.rds')
HSMM <- clusterCells(HSMM, num_clusters=as.numeric(cluster_number))
saveRDS(HSMM,'post_quality_control_data.rds')
print(plot_cell_trajectory(HSMM, color="Cluster"))
ggsave("cell_cluster_plot.png")
ggsave("cell_cluster_plot.tiff", width = 7, height = 7,dpi=600)
pData(HSMM)$Size_Factor <- NULL
rownames(pData(HSMM)) <- NULL
pData(HSMM)$Total_mRNAs <- Matrix::colSums(exprs(HSMM))
write.table(pData(HSMM), 'cluster_table_after.txt', sep="\t",quote=FALSE)
dev.off() 