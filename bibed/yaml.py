
import yaml
import logging

from yaml.representer import Representer

from bibed.ltrace import lprint, lprint_caller_name
from bibed.decorators import run_at_most_every  # only_one_when_idle
from bibed.foundations import AttributeDict
from bibed.system import touch_file


LOGGER = logging.getLogger(__name__)


class AttributeDictFromYaml(AttributeDict):
    ''' This class is meant to be subclassed.

        .warn:: Suport for `auto_save` is partial and will *never* be
            complete: when you update/modify an attribute *in-place*,
            the instance *cannot* know you dit it. In this case, you
            have to call `:meth:save` yourself.
    '''

    filename = None
    auto_save = True

    def __init__(self, *args, **kwargs):

        assert(self.filename)

        filename = self.filename

        touch_file(filename)

        ydata = yaml.load(open(filename, 'r')) or {}

        super().__init__(ydata, default=True, *args, **kwargs)

        LOGGER.debug('{0} loaded from “{1}”.'.format(
                     self.__class__.__name__, self.filename))

    def __setattr__(self, prop, val):

        # assert lprint_caller_name()
        # assert lprint(prop, val)

        super().__setattr__(prop, val)

        if self.auto_save:
            self.save()

    def __delattr__(self, prop):

        # assert lprint_caller_name()
        # assert lprint(prop, getattr(self, prop))

        super().__delattr__(prop)

        if self.auto_save:
            self.save()

    @run_at_most_every(1000)
    def save(self):

        return self.__save()

    # Method alias
    write = save

    def save_now(self):
        return self.__save()

    # Method alias
    write_now = save_now

    def __save(self):

        # assert lprint_caller_name(levels=4)

        with open(self.filename, 'w') as f:
            yaml.add_representer(type(self), Representer.represent_dict)
            yaml.add_representer(AttributeDictFromYaml,
                                 Representer.represent_dict)
            yaml.add_representer(AttributeDict, Representer.represent_dict)
            yaml.add_representer(type(None), Representer.represent_none)

            # f.write(yaml.dump(self, default_flow_style=True))
            f.write(yaml.dump(self, default_flow_style=False,
                              width=72, indent=2))

        LOGGER.debug('{0} saved to “{1}”.'.format(
                     self.__class__.__name__, self.filename))
