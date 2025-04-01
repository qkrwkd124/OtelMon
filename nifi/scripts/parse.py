import logging

import module.nifi as nifi
import module.trace_log as trace_log

@nifi.task(mode="production")
@trace_log.traced()
def parse(*args, **kwargs) :
    logging.info("===== parse start =====")

    raise Exception("Exception Error Test")
    
    return nifi.Result(
        result={},
        process_count=row_count
    )

if __name__ == "__main__":
    parse()
    