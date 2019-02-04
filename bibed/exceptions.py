

class BibedException(Exception):
    pass


class BibedError(BibedException):
    pass


# ———————————————————————————————————————————————————————————————— Stores exceptions


class BibedDataStoreException(BibedException):
    pass


class BibedFileStoreException(BibedException):
    pass


class AlreadyLoadedException(BibedFileStoreException):
    pass


class NoDatabaseForFilenameError(BibedFileStoreException):
    pass


class FileNotFoundError(BibedFileStoreException):
    pass


class BibKeyNotFoundError(BibedException):
    pass


# —————————————————————————————————————————————————————————————— Database exceptions


class BibedDatabaseException(BibedException):
    pass


class BibedDatabaseError(BibedError):
    pass


class IndexingFailedError(BibedDatabaseError):
    pass
