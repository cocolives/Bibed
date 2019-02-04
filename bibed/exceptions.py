

class BibedException(Exception):
    pass


class BibedError(BibedException):
    pass


# ———————————————————————————————————————————————————————————————— Stores exceptions


class BibedDataStoreException(BibedException):
    pass


class BibedDataStoreError(BibedError):
    pass


class BibedFileStoreException(BibedException):
    pass


class BibedFileStoreError(BibedError):
    pass


class AlreadyLoadedException(BibedFileStoreException):
    pass


class NoDatabaseForFilenameError(BibedFileStoreError):
    pass


class FileNotFoundError(BibedFileStoreError):
    pass


class BibKeyNotFoundError(BibedError):
    pass


# —————————————————————————————————————————————————————————————— Database exceptions


class BibedDatabaseException(BibedException):
    pass


class BibedDatabaseError(BibedError):
    pass


class IndexingFailedError(BibedDatabaseError):
    pass


# ——————————————————————————————————————————————————————————————————— GUI exceptions


class BibedTreeViewException(BibedException):
    pass
