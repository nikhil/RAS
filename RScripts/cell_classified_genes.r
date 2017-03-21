#Usage:
#Rscript cell_classified_genes.r gene_array
library("monocle")
args <- commandArgs(trailingOnly=TRUE)
#print(args)
if(length(args)==0)
{
	print("Usage: Rscript cell_classified_genes.r gene_array")
}
HSMM <- readRDS("classified_cells.rds")
selected_genes <- row.names(subset(fData(HSMM),gene_short_name %in% args[1:length(args)]))
print(selected_genes)
cds_subset <- HSMM[selected_genes,]
print(plot_genes_jitter(cds_subset, grouping='CellType',color_by="CellType"))
ggsave("cell_classified_genes_plot.png")
ggsave("cell_classified_genes_plot.tiff", width = 7, height = 7,dpi=600)
dev.off()
