"""Isolated in-memory database for the opt-in chatbot evaluation suite."""

from datagrapho.settings import *  # noqa: F403

DATABASES = {
    'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'},
}
