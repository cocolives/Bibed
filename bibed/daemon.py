
import logging
import multiprocessing

from bibed.store import BibedFileStore


LOGGER = logging.getLogger(__name__)


def background_process_run(queue_recv, queue_send):
    ''' HEADS UP: queues are renamed from a daemon perspective. '''

    background_app = BibedBackgroundProcess(queue_recv, queue_send)

    background_app.run()


class BibedBackgroundProcess:

    def __init__(self, queue_in, queue_out):

        self.queue_in = queue_in
        self.queue_out = queue_out

        # No data store here, we just need to write to system files.
        self.files = BibedFileStore()
        self.files.load_system_files()

        # LOGGER.debug('Background process created.')

    def run(self):

        LOGGER.info('Background process started.')

        task = self.queue_in.get()

        if task is None:
            self.queue_in.task_done()

        while task is not None:
            self.process_task(task)
            self.queue_in.task_done()
            self.queue_in.get()

        # Be sure the master process can stop.
        self.queue_in.task_done()
        self.queue_out.put(None)


class BibedDaemonMixin:

    def daemon_setup(self):

        self.__daemon_process = None
        self.__daemon_queue_send = None
        self.__daemon_queue_recv = None

    def daemon_execute(self):

        if self.__daemon_process is None:
            self.daemon_launch()

    def daemon_launch(self):

        # send from GUI to background processors
        self.__daemon_queue_send = multiprocessing.Queue()

        # receive from background processors in GUI
        self.__daemon_queue_recv = multiprocessing.Queue()

        self.__daemon_process = multiprocessing.Process(
            target=background_process_run,
            args=(self.__daemon_queue_send, self.__daemon_queue_recv)
        )

        self.__daemon_process.start()

        # Main loop interval get queue_recv.

    def daemon_quit(self):

        # If the daemon process hasn't even
        # started, don't bother quitting it.
        if self.__daemon_process is not None:
            LOGGER.info('Joining background process …')
            self.__daemon_queue_send.put(None)
            self.__daemon_process.join()
