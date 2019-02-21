
from bibed.constants import ActionStatus


class EntryActionStatusMixin:

    action_status = None

    @property
    def is_waiting(self):

        return self.action_status & ActionStatus.WAITING

    @property
    def has_error(self):

        return self.action_status & ActionStatus.ERROR
