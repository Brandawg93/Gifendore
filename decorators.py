import functools, time, asyncio, logging

logger = logging.getLogger("gifendore")

def debug(func):
	"""Print the function signature and return value"""
	@functools.wraps(func)
	def wrapper_debug(*args, **kwargs):
		args_repr = [repr(a) for a in args]                      # 1
		kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]  # 2
		signature = ", ".join(args_repr + kwargs_repr)           # 3
		logger.debug(f"Calling {func.__name__}({signature})")
		value = func(*args, **kwargs)
		logger.debug(f"{func.__name__!r} returned {value!r}")           # 4
		return value
	return wrapper_debug

def timer(func):
	"""Print the runtime of the decorated function"""
	@functools.wraps(func)
	def wrapper_timer(*args, **kwargs):
		start_time = time.perf_counter()    # 1
		value = func(*args, **kwargs)
		end_time = time.perf_counter()      # 2
		run_time = end_time - start_time    # 3
		logger.debug(f"Finished {func.__name__!r} in {run_time:.4f} secs")
		return value
	return wrapper_timer

def async_timer(func):
	"""Print the runtime of the decorated function"""
	@functools.wraps(func)
	async def wrapper_timer(*args, **kwargs):
		start_time = time.perf_counter()    # 1
		value = await func(*args, **kwargs)
		end_time = time.perf_counter()      # 2
		run_time = end_time - start_time    # 3
		logger.debug(f"Finished {func.__name__!r} in {run_time:.4f} secs")
		return value
	return wrapper_timer
