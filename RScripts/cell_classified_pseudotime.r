#Usage:
#Rscript cell_classified_pseudotime.r num_dimension gene_array
library("monocle")
args <- commandArgs(trailingOnly=TRUE)
#print(args)
if(length(args)==0)
{
	print("Usage: Rscript cell_classified_pseudotime.r num_dimension gene_array")
}
HSMM <- readRDS("classified_cells.rds")
HSMM_myo <- reduceDimension(HSMM, max_components=as.numeric(args[1]))
HSMM_myo <- orderCells(HSMM_myo, reverse=FALSE)
selected_genes <- row.names(subset(fData(HSMM_myo),gene_short_name %in% args[2:length(args)]))
cds_subset <- HSMM_myo[selected_genes,]
print(plot_genes_in_pseudotime(cds_subset, color_by="CellType"))
ggsave("cell_classified_pseudotime_plot.png")
ggsave("cell_classified_pseudotime_plot.tiff", width = 7, height = 7,dpi=600)
dev.off()
