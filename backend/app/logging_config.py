import logging
import sys
import structlog
from typing import Any, Dict

def strip_stack_trace_in_prod(logger: Any, name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Production security safety: strips out full Python traceback stack traces 
    from the logs to prevent directory/context structure disclosures.
    """
    if "exception" in event_dict:
        event_dict["exception_summary"] = str(event_dict["exception"]).split("\n")[-1]
        del event_dict["exception"]
    if "exc_info" in event_dict:
        event_dict["exc_info_occurred"] = True
        del event_dict["exc_info"]
    return event_dict

def configure_logging():
    # Clear existing handlers
    root_logger = logging.getLogger()
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)

    # Base logging config sending to standard output
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            # Custom stack trace stripping for production safety
            strip_stack_trace_in_prod,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
