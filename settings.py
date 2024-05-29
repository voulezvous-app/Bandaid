
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # Google
    g_project_id: str = 'voulez-vous-97921'
    g_client_email: str = 'firebase-adminsdk-xiqc4@voulez-vous-97921.iam.gserviceaccount.com'
    g_private_key_id: str = ''
    g_private_key: str = ''
    g_client_id: str = '112245622141301611366'
    g_auth_uri: str = 'https://accounts.google.com/o/oauth2/auth'
    g_token_uri: str = 'https://oauth2.googleapis.com/token'
    g_auth_provider_x509_cert_url: str = 'https://www.googleapis.com/oauth2/v1/certs'
    g_client_x509_cert_url: str = 'https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-xiqc4%40voulez-vous-97921.iam.gserviceaccount.com'


    # Firebase Creds
    @property
    def firebase_credentials(self):
        return {
            'type': 'service_account',
            'project_id': self.g_project_id,
            'private_key_id': self.g_private_key_id,
            'private_key': self.g_private_key.replace('\\n', '\n'),
            'client_email': self.g_client_email,
            'client_id': self.g_client_id,
            'auth_uri': self.g_auth_uri,
            'token_uri': self.g_token_uri,
            'auth_provider_x509_cert_url': self.g_auth_provider_x509_cert_url,
            'client_x509_cert_url': self.g_client_x509_cert_url,
        }

    model_config = SettingsConfigDict(env_file='.env', extra='allow')
