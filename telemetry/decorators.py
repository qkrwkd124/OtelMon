import time
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from functools import wraps
def otel_traced(func):
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        
        tracer = trace.get_tracer(__name__)
        span_name = func.__name__
        
        with tracer.start_as_current_span(span_name) as span:
            try :
                start_time = time.time()
                
                result = func(*args, **kwargs)
                span.set_attribute("result", result)
                
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise e
            finally :
                span
                
                
        return func(*args, **kwargs)
    return wrapper

