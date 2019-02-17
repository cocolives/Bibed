
import os
import gzip


class GZipNamer:

    def __call__(self, default_filename):

        return default_filename + '.gz'


class GZipRotator:
    ''' Inspired from https://stackoverflow.com/a/16461440/654755 '''

    def __call__(self, source, destination):

        os.rename(source, destination)

        gziped_destination = '{}.gz'.format(destination)

        with open(destination, 'rb') as file_in, \
                gzip.open(gziped_destination, 'wb') as file_out:
            file_out.writelines(file_in)

        os.rename(gziped_destination, destination)
