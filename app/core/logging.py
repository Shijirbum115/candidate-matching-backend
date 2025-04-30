# Logging setup
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .config import get_settings

settings = get_settings()


class SearchLogFormatter(logging.Formatter):
    """Custom formatter for search metrics logging."""
    
    def format(self, record):
        if not hasattr(record, 'search_metrics'):
            return super().format(record)
        
        metrics = record.search_metrics
        timestamp = datetime.now().isoformat()
        
        # Format the search metrics as JSON
        log_entry = {
            "timestamp": timestamp,
            "query": metrics.get("query", ""),
            "query_en": metrics.get("query_en", ""),
            "num_candidates_processed": metrics.get("num_candidates_processed", 0),
            "num_results_returned": metrics.get("num_results_returned", 0),
            "processing_time_ms": metrics.get("processing_time_ms", 0),
            "score_threshold": metrics.get("score_threshold", 0),
            "weights": metrics.get("weights", {}),
            "candidates": metrics.get("candidates", [])
        }
        
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging():
    """Configure application logging."""
    # Create logs directory if it doesn't exist
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(exist_ok=True)
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)
    
    # Console handler for standard logs
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.LOG_LEVEL)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for general logs
    app_log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}_app.log"
    file_handler = logging.FileHandler(app_log_file, encoding='utf-8')
    file_handler.setLevel(settings.LOG_LEVEL)
    file_handler.setFormatter(console_formatter)
    root_logger.addHandler(file_handler)
    
    # Special handler for search metrics
    search_logger = logging.getLogger("search_metrics")
    search_logger.setLevel(logging.INFO)
    search_logger.propagate = False
    
    search_log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}_search_metrics.json"
    search_handler = logging.FileHandler(search_log_file, encoding='utf-8')
    search_handler.setLevel(logging.INFO)
    search_handler.setFormatter(SearchLogFormatter())
    search_logger.addHandler(search_handler)
    
    return root_logger


def get_search_logger():
    """Get the search metrics logger."""
    return logging.getLogger("search_metrics")


def log_search_metrics(
    query: str,
    query_en: str,
    num_candidates_processed: int,
    num_results_returned: int,
    processing_time_ms: float,
    score_threshold: float,
    weights: Dict[str, float],
    candidates: List[Dict[str, Any]],
):
    """Log detailed search metrics to the search metrics log file."""
    logger = get_search_logger()
    
    search_metrics = {
        "query": query,
        "query_en": query_en,
        "num_candidates_processed": num_candidates_processed,
        "num_results_returned": num_results_returned,
        "processing_time_ms": processing_time_ms,
        "score_threshold": score_threshold,
        "weights": weights,
        "candidates": candidates
    }
    
    # Create a log record with custom search_metrics attribute
    record = logging.LogRecord(
        name="search_metrics",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="",
        args=(),
        exc_info=None
    )
    record.search_metrics = search_metrics
    
    # Process the record through the logger
    logger.handle(record)