from abc import abstractmethod, ABCMeta
from typing import List, Dict


class Mail(metaclass=ABCMeta):
    @abstractmethod
    def send_email(self, to: List[str], body: str = None, subject: str = None, attachments: Dict[str, str] = None,
                   save: bool = True, **kwargs):
        pass
