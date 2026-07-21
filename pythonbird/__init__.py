from importlib.metadata import PackageNotFoundError, version

from .client import Thunderbird
from .contacts import ThunderbirdContacts, ThunderbirdContactsError
from .core import ThunderbirdLinux
from .mail import ThunderbirdMail
from .models import Attachment, Contact, Message

try:
    __version__ = version("pythonbird")
except PackageNotFoundError:
    __version__ = "0.3.0.dev0"

__all__ = [
    "__version__",
    "Thunderbird",
    "ThunderbirdLinux",
    "ThunderbirdMail",
    "ThunderbirdContacts",
    "ThunderbirdContactsError",
    "Message",
    "Attachment",
    "Contact",
]
