from typing import List, Dict

from exchangelib import Account, Configuration, Credentials, DELEGATE, Mailbox, Message
from exchangelib.attachments import FileAttachment

from management_tools.email.base import Mail


class ExchangeMail(Mail):
    def __init__(self, username: str, password: str, address: str, ews_url: str, ews_auth_type: str):
        credentials = Credentials(username=username, password=password)
        config = Configuration(service_endpoint=ews_url, credentials=credentials, auth_type=ews_auth_type)
        self.account = Account(primary_smtp_address=address, config=config, autodiscover=False, access_type=DELEGATE)

    def _create_mail(self, to: List[str], **kwargs) -> Message:
        return Message(account=self.account, to_recipients=[Mailbox(email_address=i) for i in to], **kwargs)

    def _attach(self, message: Message, attachments: Dict[str, str]):
        for name, attachment in attachments.items():
            with open(attachment) as f:
                message.attach(FileAttachment(name=name, content=f.read().encode('utf-8')))

    def send_email(self, to: List[str], body: str = None, subject: str = None, attachments: Dict[str, str] = None,
                   save: bool = True, **kwargs):
        """
        Send an email to given addresses.

        All files defined in *attachments* dictionary will be attached to mail. This dictionary specifies the name of
        the attachment and the path of the file to be attached.

        If *save* is True, the message will be stored at sent folder after send it.

        :param to: Addresses list to send email.
        :param body: Message body.
        :param subject: Message subject
        :param attachments: Files to be attached.
        :param save: Defines if message will be saved after sent.
        :param kwargs: Message kwargs.
        """
        if save:
            kwargs['folder'] = self.account.sent

        message = self._create_mail(to=to, body=body, subject=subject, **kwargs)
        self._attach(message, attachments)

        if save:
            message.send_and_save()
        else:
            message.send()
