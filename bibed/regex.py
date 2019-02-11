
import re


OWNER_NAME_RE = re.compile('^[a-z]([- :,@_a-z0-9]){2,}$', re.IGNORECASE)
