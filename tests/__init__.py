from functools import wraps


def fails(test):
    """Assert the decorated test either fails or errors."""
    @wraps(test)
    def wrapper(*args, **kwargs):
        try:
            ret = test(*args, **kwargs)
        except SystemExit, KeyboardInterrupt:
            raise
        except:
            # Swallow all other errors. It's supposed to have errors, Assertion
            # or otherwise.
            pass
        else:
            raise AssertionError("Expected a failure or error but didn't get one.")

    return wrapper
