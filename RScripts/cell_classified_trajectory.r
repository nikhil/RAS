#Usage:
#Rscript cell_classified_trajectory.r dimension_number
library("monocle")
library("reshape")
library('ggplot2')
args <- commandArgs(trailingOnly=TRUE)
if(length(args)==0)
{
	print("Usage: Rscript cell_classified_trajectory.r dimension_number")
}
dimension_number <- args[1]
HSMM <- readRDS("classified_cells.rds")
HSMM <- reduceDimension(HSMM, max_components=as.numeric(dimension_number))
HSMM <- orderCells(HSMM, reverse=FALSE)
print(plot_cell_trajectory(HSMM, color_by="CellType"))
ggsave("cell_classified_trajectory_plot.png")
ggsave("cell_classified_trajectory_plot.tiff", width = 7, height = 7,dpi=600)
dev.off() 