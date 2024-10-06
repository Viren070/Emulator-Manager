"""
This is the ProgressHandler class for the GUI

For the GUI, our progress handler will be a progress bar that updates as the progress is reported.
The progress handler will have a report_progress method that will have to take the completed_data as an argument.
The report_progress method will then update the progress bar with the new values

We need to create the progress bar class.
"""
from time import perf_counter

from core.logging.logger import Logger



class ProgressHandler:
    def __init__(self):
        self.logger = Logger(__name__).get_logger()
        self.smoothing_factor = 0.3
        self._operation_start_time = 0
        self._units = ""
        self._total_units = 0
        self._last_speed = 0
        self._average_speed = 0
        self._current_units = 0
        self._should_cancel = False

    def start_operation(self, title, total_units, units, status="Starting..."):

        self._average_speed = 0
        self._total_units = total_units
        self._should_cancel = False
        self._units = units
        self._current_units = 0
        self._last_speed = 0
        self._operation_start_time = perf_counter()



    def is_total_units_set(self):
        return self._total_units > 0

    def set_total_units(self, total_units):
        self._total_units = total_units

    def report_progress(self, completed_units):

        self._current_units = completed_units
        # update progress bar, percentage and progress label


        # calculate download speed
        last_speed = completed_units / (
            (perf_counter() - self._operation_start_time)
        )
        # use exponential moving average to calculate download speed
        self._average_speed = (
            self.smoothing_factor * last_speed +

            (1 - self.smoothing_factor) * self._average_speed
        )

        # calculate time left
        if self._average_speed != 0:
            time_left = (self._total_units - completed_units) / self._average_speed
            minutes, seconds = divmod(int(time_left), 60)
            hours, minutes = divmod(minutes, 60)
            time_left_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            time_left_str = "00:00:00"
        
        self.print_progress_bar(completed_units, self._total_units, prefix='Progress:', suffix='Complete', length=50)

    def print_progress_bar(self, iteration, total, prefix='', suffix='', decimals=1, length=50, fill='█'):
        """
        Call in a loop to create terminal progress bar
        @params:
            iteration   - Required  : current iteration (Int)
            total       - Required  : total iterations (Int)
            prefix      - Optional  : prefix string (Str)
            suffix      - Optional  : suffix string (Str)
            decimals    - Optional  : positive number of decimals in percent complete (Int)
            length      - Optional  : character length of bar (Int)
            fill        - Optional  : bar fill character (Str)
        """
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filled_length = int(length * iteration // total)
        bar = fill * filled_length + '-' * (length - filled_length)
        print(f'\r{prefix} |{bar}| {percent}% {suffix}', end='\r')
        # Print New Line on Complete
        if iteration == total:
            print()

    def report_success(self):
        pass

    def report_error(self, error):
        pass

    def report_configure(self, widget, **kwargs):
        pass


    def should_cancel(self):
        return self._should_cancel

    def send_cancel_signal_to_operation(self):
        """
        called by external events like cancel buttons to signal the operation to cancel
        """
        self._should_cancel = True
        self.set_cancel_button_state("disabled")

    def cancel(self):
        """
        called by the operation
        """
        pass
