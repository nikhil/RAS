library(cummeRbund)
args <- commandArgs(trailingOnly=TRUE)
error_file <- file(args[1], open="wt")
sink(error_file, type="message")
cuff <- readCufflinks()
sig_genes <- readRDS('significant_genes.rds')
k_means_cluster<-csCluster(sig_genes,k=as.numeric(args[3]))
Cluster_Num <- k_means_cluster$cluster
Cluster_Num <- Cluster_Num[order(Cluster_Num)]
k_means_cluster_data <- data.frame(Cluster_Num)
write.table(k_means_cluster_data, 'k_means_cluster.txt', sep="\t",quote=FALSE)
k_means_cluster_plot <- csClusterPlot(k_means_cluster)
png(args[2],width = 10, height = 10, units= 'in',res=600)
print(k_means_cluster_plot)
dev.off()

