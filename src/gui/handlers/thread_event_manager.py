import queue
import threading
import traceback

from core.logging.logger import Logger


class ThreadEventManager:
    def __init__(self, window):
        self.logger = Logger(__name__).get_logger()
        self.events = []
        self.window = window
        self.result_queue = queue.Queue()

    def is_event_running(self, event_id):
        for event in self.events:
            if event["id"] == event_id:
                return True
        return False

    def add_event(self, event_id, func, kwargs=None, completion_functions=None, error_functions=None, completion_funcs_with_result=None, ignore_messages=False):
        event = {
            "id": event_id,
            "function": func,
            "kwargs": kwargs if kwargs else {},
            "completion_functions": completion_functions if completion_functions else [],
            "completion_func_with_result": completion_funcs_with_result if completion_funcs_with_result else [],
            "error_functions": error_functions if error_functions else [],
            "ignore_messages": ignore_messages,
            "output_queue": queue.Queue(),
            "error_during_run": False
        }
        self.events.append(event)
        self.start_event(event)

    def start_event(self, event):
        self.logger.info(f"Starting event: {event["id"]}")
        thread = threading.Thread(target=self._run_event, args=(event,))
        thread.start()
        self._main_thread_loop(event)

    def _run_event(self, event):
        try:
            output = event["function"](**event["kwargs"])
        except Exception as e:
            self.logger.error(f"Error in event {event["id"]}: {e} \n{traceback.format_exc()}")
            event["error_during_run"] = True
            output = None

        self.logger.info(f"Event completed: {event["id"]}")
        if output is None:
            output = {}

        if not output:
            self.logger.warning(f"Event {event["id"]} returned no result")

        event["output_queue"].put(output)

    def _main_thread_loop(self, event):
        if not event["output_queue"].empty():
            self.logger.info(f"Processing output for event: {event["id"]}")
            output = event["output_queue"].get()
            self._process_output(output, event)
            return
        self.window.after(50, self._main_thread_loop, event)

    def _process_output(self, output, event):
        # Assuming result is a dictionary with keys "message_func" and "message_args"
        # where both can be None for no message
        message = output.get("message")
        result = output.get("result")

        # if there was an unhandled error during the event, run the error functions if provided
        if event["error_during_run"] and event["error_functions"] and not event["ignore_messages"]:
            for error_func in event["error_functions"]:
                error_func()

        if message and not event["ignore_messages"]:
            message["function"](*message["arguments"])

        # run the completion functions
        for completion_func in event["completion_functions"]:
            completion_func()

        # if a completion function with result was provided, run it
        # and pass the result of the event to it
        # only if there was no error during the event
        if event["completion_func_with_result"] and not event["error_during_run"]:
            for completion_func in event["completion_func_with_result"]:
                completion_func(*result)

        # Remove the event from the list of events
        self.events.remove(event)
        self.logger.info(f"{event["id"]} event result processed and removed from event list")
