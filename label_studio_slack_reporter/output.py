'''Reporters
'''
from abc import ABC, abstractmethod

from slack_sdk import WebClient


class AbstractOutput(ABC):
    """Abstract Output Job

    """

    def __init__(self,
                 schedule: str,
                 job_name: str,
                 **kwargs):
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
