# V3.7.41 cross-language independent verification with actual CRAN packages.
# Usage: Rscript ci/cafast_verify_v3741.R <directory-with-CA_5x10_t*.csv>
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1L) stop("directory argument required")
if (!requireNamespace("cafast", quietly = TRUE)) stop("cafast not installed")
if (!requireNamespace("caverify", quietly = TRUE)) stop("caverify not installed")
if (utils::packageVersion("cafast") < "0.1.1") stop("cafast 0.1.1 or later required")
input_dir <- args[[1L]]
records <- list()
for (t in 2:4) {
  path <- file.path(input_dir, sprintf("CA_5x10_t%d.csv", t))
  x <- as.matrix(utils::read.csv(path, header = FALSE, colClasses = rep("integer", 5)))
  if (ncol(x) != 5L || any(is.na(x)) || any(x < 0L | x > 9L)) stop("invalid CSV digits")
  result <- cafast::count_core(x, t = t, vs = rep(10L, 5L), rowmult = TRUE)
  verify <- caverify::ca_verify(x, t = t, v = rep(10L, 5L), threads = 1L)
  if (any(result$missing != 0L) || !isTRUE(verify$covered)) {
    stop(sprintf("coverage failure at strength %d", t))
  }
  singleton <- sum(result$rowmult == 1L)
  cat(sprintf("CAFV3741 strength=%d rows=%d missing=%d covered=%s singleton_cell_count=%d cafast=%s caverify=%s\n",
              t, nrow(x), sum(result$missing), as.character(verify$covered),
              singleton, as.character(utils::packageVersion("cafast")),
              as.character(utils::packageVersion("caverify"))))
  records[[as.character(t)]] <- data.frame(
    strength = t, rows = nrow(x), missing = sum(result$missing),
    caverify_ok = isTRUE(verify$covered),
    singleton_cell_count = singleton,
    cafast_version = as.character(utils::packageVersion("cafast")),
    caverify_version = as.character(utils::packageVersion("caverify"))
  )
}
utils::write.csv(do.call(rbind, records),
                 file.path(input_dir, "cafast_caverify_verified.csv"),
                 row.names = FALSE, quote = FALSE)
