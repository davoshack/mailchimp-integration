import hashlib
import logging

from django.shortcuts import render
from django.contrib import messages

from django.conf import settings
from mailchimp_marketing import Client
from mailchimp_marketing.api_client import ApiClientError

logger = logging.getLogger(__name__)


def get_subscriber_hash(member_email):
    # Helper function for generating email hash
    member_email = member_email.lower().encode()
    m = hashlib.md5(member_email)
    return m.hexdigest()


class MailChimpClient:
    """
    Class that handle the communication to the mailchimp API.
    """
    def __init__(self):
        self.client = Client()
        self.user_email = ''
        self.api_key = settings.MAILCHIMP_API_KEY
        self.server_prefix = settings.MAILCHIMP_DATA_CENTER
        self.audience_id = settings.MAILCHIMP_EMAIL_LIST_ID
        self.tag_list = settings.MAILCHIMP_DEFAULT_TAGS
        self.tag_status = 'active'

    def set_tag_list(self, tag_list: tuple, status: str = 'active') -> None:
        # This method can be used to ovewrite default tag list
        self.tag_list = tag_list
        self.tag_status = status

    def _get_tag_list(self) -> list:
        tags = [{'name': tag, 'status': self.tag_status} for tag in self.tag_list]
        return tags

    def set_auth_client(self):
        try:
            # Basic Auth
            self.client.set_config({
                "api_key": self.api_key,
                "server": self.server_prefix,
            })

            # OAuth2
            """
            self.client.set_config({
                "access_token": "ACCESS_TOKEN",
                "server": "SERVER_PREFIX"
            })
            """
        except ApiClientError as error:
            raise Exception("A mailchimp exception occurred: {}".format(error.text))

    def subscribe_new_member(self, user_email: str) -> None:
        """
        Method that add an email user to an audience ID and
        """
        self.user_email = user_email
        member_info = {
            "email_address": self.user_email,
            "status": "subscribed",
        }
        try:
            self.client.lists.add_list_member(self.audience_id, member_info)
        except ApiClientError as error:
            logger.exception(
                f'Mailchimp: The user with the email: {user_email} '
                f'could not be subscribed to audience id: {self.audience_id}.')
            raise Exception("A mailchimp exception occurred: {}".format(error.text))

    def add_member_to_tags(self) -> None:
        """
        Method that update list member tags.
        """
        tags = self._get_tag_list()
        body = {
            'tags': tags
        }
        subscriber_hash = get_subscriber_hash(self.user_email)
        try:
            self.client.lists.update_list_member_tags(self.audience_id,
                                                      subscriber_hash, body)
        except ApiClientError as error:
            logger.exception(
                f'Mailchimp: The member with the email: {self.user_email} '
                f'could not be added to the following tags: {self.tag_list}.')
            raise Exception("A mailchimp exception occurred: {}".format(error.text))


def subscription(request):
    if request.method == "POST":
        user_email = request.POST['email']
        mailchimp_client = MailChimpClient()
        mailchimp_client.set_auth_client()
        mailchimp_client.subscribe_new_member(user_email)
        mailchimp_client.add_member_to_tags()
        messages.success(request, "Email received. thank You! ") # message

    return render(request, "marketing/index.html")

