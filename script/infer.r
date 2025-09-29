#!/usr/bin/env Rscript
# inference_means_by_trace.R
# Paired t-test inference for Means_<trace>.csv files in output/
#
# Produces: output/Inference_<trace>.csv for each Means_<trace>.csv
#
# Assumes Means CSV layout:
# segment,lru,rand,clock,optimal
# 1-200,0.0644,0.0806,0.0678,0.0431
# ...

# ---- USER SETTINGS ----
input_dir <- "output"
file_pattern <- "^Means_(.+)\\.csv$"  # captures trace name
algo_order <- c("lru","rand","clock","optimal")
round_digits <- 4
# -----------------------

# helpers
safe_read <- function(path) {
  tryCatch(read.csv(path, stringsAsFactors = FALSE, check.names = FALSE),
           error = function(e) {
             message("Failed to read: ", path, " : ", e$message)
             NULL
           })
}

paired_cohen_d <- function(diff_vec) {
  # paired Cohen's d = mean(diff) / sd(diff)
  s <- sd(diff_vec, na.rm = TRUE)
  if (is.na(s) || s == 0) return(NA_real_)
  mean(diff_vec, na.rm = TRUE) / s
}

process_file <- function(path) {
  df <- safe_read(path)
  if (is.null(df)) return(NULL)

  # get trace name from filename
  fname <- basename(path)
  trace_match <- regmatches(fname, regexec(file_pattern, fname))[[1]]
  if (length(trace_match) < 2) {
    message("Skipping file with unexpected name: ", fname)
    return(NULL)
  }
  trace_name <- trace_match[2]

  # identify algorithm columns
  cols <- colnames(df)
  algos_present <- intersect(algo_order, tolower(cols)) # case-insensitive match
  # if first column is 'segment', drop it
  if ("segment" %in% tolower(cols)) {
    # find actual column names that correspond
    # assume the first column name 'segment' (case-insensitive)
    seg_idx <- which(tolower(cols) == "segment")[1]
    if (!is.na(seg_idx)) {
      df <- df[ , -seg_idx, drop = FALSE]
      cols <- colnames(df)
    }
  }

  # Now determine algos actually present (exact names)
  algos_present <- intersect(algo_order, tolower(colnames(df)))
  if (length(algos_present) < 2) {
    message("Not enough algorithm columns in ", fname, " — need at least 2. Skipping.")
    return(NULL)
  }

  # ensure order and get vectors
  # map to actual column names (case-insensitive)
  col_map <- setNames(colnames(df), tolower(colnames(df)))
  algos_to_use <- algo_order[algo_order %in% tolower(colnames(df))]
  # build tidy data frame for tests
  results_list <- list()
  pairs <- combn(algos_to_use, 2, simplify = FALSE)

  n_rows <- nrow(df)
  if (n_rows < 2) warning("Very small sample size (n = ", n_rows, ") in ", fname, " — tests may be unreliable.")

  for (p in pairs) {
    a <- p[1]; b <- p[2]
    col_a <- col_map[[a]]
    col_b <- col_map[[b]]
    vec_a <- as.numeric(df[[col_a]])
    vec_b <- as.numeric(df[[col_b]])
    # paired differences (a - b)
    diff_ab <- vec_a - vec_b

    # Shapiro-Wilk for differences (if n >= 3)
    shapiro_p <- if (length(na.omit(diff_ab)) >= 3) {
      tryCatch(shapiro.test(diff_ab)$p.value, error = function(e) NA_real_)
    } else NA_real_

    # Paired t-test (two-sided)
    t_res <- tryCatch(t.test(vec_a, vec_b, paired = TRUE),
                      error = function(e) e)
    if (inherits(t_res, "htest")) {
      t_stat <- as.numeric(t_res$statistic)
      df_t <- as.numeric(t_res$parameter)
      p_value <- as.numeric(t_res$p.value)
      conf <- t_res$conf.int
      conf_low <- conf[1]; conf_high <- conf[2]
      mean_diff <- mean(diff_ab, na.rm = TRUE)
      estimate <- as.numeric(t_res$estimate)  # for paired t.test this is mean of differences
    } else {
      t_stat <- NA_real_; df_t <- NA_real_; p_value <- NA_real_
      conf_low <- NA_real_; conf_high <- NA_real_; mean_diff <- mean(diff_ab, na.rm = TRUE); estimate <- NA_real_
    }

    # Wilcoxon signed-rank as fallback (paired)
    wilcox_p <- tryCatch(wilcox.test(vec_a, vec_b, paired = TRUE)$p.value,
                         error = function(e) NA_real_)

    # Cohen's d for paired samples
    cohen_d <- paired_cohen_d(diff_ab)

    results_list[[paste(a, "vs", b, sep = "_")]] <- data.frame(
      comparison = paste(a, "vs", b, sep = "_"),
      n = length(na.omit(diff_ab)),
      t_stat = t_stat,
      df = df_t,
      p_value = p_value,
      mean_diff = mean_diff,
      conf_low = conf_low,
      conf_high = conf_high,
      cohen_d = cohen_d,
      shapiro_p = shapiro_p,
      wilcox_p = wilcox_p,
      stringsAsFactors = FALSE
    )
  }

  res_df <- do.call(rbind, results_list)
  row.names(res_df) <- NULL

  # multiple comparisons adjustments
  res_df$p_adj_bonferroni <- p.adjust(res_df$p_value, method = "bonferroni")
  res_df$p_adj_holm <- p.adjust(res_df$p_value, method = "holm")
  res_df$p_adj_bh <- p.adjust(res_df$p_value, method = "BH")

  # Round numeric columns for neat CSV output
  num_cols <- c("t_stat","df","p_value","mean_diff","conf_low","conf_high","cohen_d","shapiro_p","wilcox_p",
                "p_adj_bonferroni","p_adj_holm","p_adj_bh")
  for (nc in num_cols) {
    if (nc %in% colnames(res_df)) {
      res_df[[nc]] <- round(res_df[[nc]], digits = round_digits)
    }
  }

  # write output CSV
  out_fname <- file.path(input_dir, paste0("Inference_", trace_name, ".csv"))
  write.csv(res_df, out_fname, row.names = FALSE, na = "")
  message("Wrote inference file: ", out_fname)
  return(res_df)
}

# Main: find Means_*.csv and process each
files <- list.files(path = input_dir, pattern = "^Means_.+\\.csv$", full.names = TRUE)
if (length(files) == 0) {
  stop("No Means_*.csv files found in ", input_dir)
}

all_outputs <- list()
for (f in files) {
  message("Processing: ", f)
  out <- process_file(f)
  all_outputs[[basename(f)]] <- out
}

message("Done. Inference files written to: ", input_dir)