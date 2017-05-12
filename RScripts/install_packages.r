#Usage:
#Rscript install_packages.r
source("https://bioconductor.org/biocLite.R")
biocLite()
if(!require("monocle")) {
	biocLite("monocle")
	library("monocle")

}
if(!require("cummeRbund")) {
	biocLite("cummeRbund")
	library("cummeRbund")
	
}
if(!require("reshape")) {
	install.packages("reshape",repos = "http://cran.us.r-project.org")
	library("reshape")
	
}
if(!require("ggplot2")) {
	install.packages("ggplot2",repos = "http://cran.us.r-project.org")
	library("ggplot2")
	
}
if(!require("pheatmap")) {
	install.packages("pheatmap",repos = "http://cran.us.r-project.org")
	library("pheatmap")
	
}




