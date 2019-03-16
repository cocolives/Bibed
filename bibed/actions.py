
from bibed.constants import ActionStatus, BibAttrs


class EntryActionStatusMixin:

    __action_status = None

    @property
    def action_status(self):

        return self.__action_status

    @action_status.setter
    def action_status(self, value):

        self.__action_status = value

        self.update_store_row({BibAttrs.COLOR: self.context_color})

    @property
    def is_running(self):

        return self.action_status & ActionStatus.RUNNING

    @property
    def is_waiting(self):

        return self.action_status & ActionStatus.WAITING

    @property
    def has_error(self):

        return self.action_status & ActionStatus.ERROR
