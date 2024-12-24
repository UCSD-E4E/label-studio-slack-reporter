'''Reporters
'''
import base64
from abc import ABC, abstractmethod
from email.mime.text import MIMEText
from typing import List

from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
from slack_sdk import WebClient

from label_studio_slack_reporter.gapp import GoogleAppService


class AbstractOutput(ABC):
    """Abstract Output Job

    """
    # pylint: disable=too-few-public-methods
    def __init__(self,
                 schedule: str,
                 job_name: str,
                 **_):
        self.schedule = schedule
        self.name = job_name

    @abstractmethod
    def execute(self,
                message: str):
        """Executes outputting

        Args:
            message (str): Message to send.  This message is a plain text
            formatted message for all relevant projects for this output job
        """


class SlackOutput(AbstractOutput):
    """Slack output
    """
    # pylint: disable=too-few-public-methods

    def __init__(self,
                 schedule: str,
                 job_name: str,
                 secret: str,
                 channel_id: str,
                 **kwargs):
        super().__init__(schedule, job_name, **kwargs)
        self.__slack_secret = secret
        self.__channel_id = channel_id

        self.__client = WebClient(token=self.__slack_secret)

    def execute(self, message):
        self.__client.chat_postMessage(
            channel=self.__channel_id,
            text=message
        )


class EmailOutput(AbstractOutput):
    """Email Output
    """
    # pylint: disable=too-few-public-methods

    def __init__(self,
                 schedule: str,
                 job_name: str,
                 subject: str,
                 to: List[str],
                 cc: List[str] = None,
                 bcc: List[str] = None,
                 **kwargs):
        # pylint: disable=too-many-arguments,too-many-positional-arguments
        super().__init__(schedule, job_name, **kwargs)
        self.__subject = subject
        self.__to = to
        self.__cc = cc
        self.__bcc = bcc

    def execute(self, message):
        gmail_service = GoogleAppService.get_instance().get_gmail_service()
        message_service: Resource = gmail_service.users().messages()
        email_message = MIMEText(message, 'plain')
        email_message['from'] = 'e4e@ucsd.edu'
        if len(self.__to) > 0:
            email_message['to'] = '; '.join(self.__to)
        if self.__cc and len(self.__cc) > 0:
            email_message['cc'] = '; '.join(self.__cc)
        if self.__bcc and len(self.__bcc) > 0:
            email_message['bcc'] = '; '.join(self.__bcc)
        email_message['subject'] = self.__subject
        try:
            message_service.send(
                userId='me',
                body={'raw': base64.urlsafe_b64encode(
                    email_message.as_bytes()).decode()}
            ).execute()
        except HttpError as exc:
            raise exc
