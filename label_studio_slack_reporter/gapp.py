'''Google Application Interface
'''
from __future__ import annotations

import logging
from argparse import ArgumentParser
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

from label_studio_slack_reporter.exceptions import (
    GmailServiceCreateFail, GoogleAppCredentialsNotFound)


class GoogleAppService:
    """Google App Service
    """
    GOOGLE_API_SCOPES = [
        'https://www.googleapis.com/auth/gmail.send',
    ]

    __instance: Optional[GoogleAppService] = None

    @classmethod
    def get_instance(cls) -> GoogleAppService:
        """Retrieves the singleton instance

        Raises:
            RuntimeError: Singleton is not initialized

        Returns:
            GoogleAppService: Singleton instance
        """
        if not cls.__instance:
            raise RuntimeError
        return cls.__instance

    def __init__(self,
                 credentials: Path,
                 token: Path):
        if self.__instance is not None:
            raise RuntimeError('Singleton violation')
        if not credentials.is_file():
            raise GoogleAppCredentialsNotFound(credentials.as_posix())

        self.__creds_path = credentials
        self.__token_path = token
        self.__token: Optional[Credentials] = None
        self.__log = logging.getLogger('GoogleAppService')

        self.load()
        GoogleAppService.__instance = self

    def load(self):
        """Loads and refreshes the tokens
        """
        if self.__token_path.is_file():
            self.__token = Credentials.from_authorized_user_file(
                filename=self.__token_path.as_posix(),
                scopes=self.GOOGLE_API_SCOPES)
        if not self.__token or not self.__token.valid:
            if (self.__token and
                self.__token.expired and
                    self.__token.refresh_token):
                self.__token.refresh(request=Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secrets_file=self.__creds_path.as_posix(),
                    scopes=self.GOOGLE_API_SCOPES
                )
                self.__token = flow.run_local_server()
            with open(self.__token_path, 'w', encoding='utf-8') as handle:
                handle.write(self.__token.to_json())

    def get_gmail_service(self) -> Resource:
        """Retrieves the gmail service

        Raises:
            GmailServiceCreateFail: On service creation failure

        Returns:
            Resource: Gmail Service Resource
        """
        self.load()
        try:
            service: Resource = build(
                serviceName='gmail',
                version='v1',
                credentials=self.__token
            )
        except HttpError as exc:
            self.__log.exception(
                'Failed to retrieve gmail service due to %s', exc)
            raise GmailServiceCreateFail from exc
        return service


def run_cli_gapp():
    """Run Gapp CLI Load
    """
    parser = ArgumentParser()
    parser.add_argument('credentials', type=Path)
    parser.add_argument('token', type=Path)

    args = vars(parser.parse_args())
    GoogleAppService(**args)


if __name__ == '__main__':
    run_cli_gapp()
