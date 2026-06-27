from importlib import import_module
from typing import List
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def load_active_domains(tool_registry):
    active_domains = settings.CHATBOT_CONFIG.get('ACTIVE_DOMAINS', ['wine'])
    
    logger.info(f"Loading active domains: {active_domains}")
    
    for domain_name in active_domains:
        try:
            tools_module = import_module(f'chatbot.domains.{domain_name}.tools')
            
            register_func = getattr(tools_module, f'register_{domain_name}_tools')
            register_func(tool_registry)
            
            logger.info(f"Successfully loaded domain: {domain_name}")
            
        except ImportError as e:
            logger.error(f"Failed to import domain '{domain_name}': {e}")
            raise
        except AttributeError as e:
            logger.error(f"Domain '{domain_name}' missing register function: {e}")
            raise


def get_domain_repository(domain_name: str):
    try:
        repository_module = import_module(f'chatbot.domains.{domain_name}.repository')
        repository_class = getattr(repository_module, f'{domain_name.capitalize()}Repository')
        return repository_class()
    except (ImportError, AttributeError) as e:
        logger.error(f"Failed to load repository for domain '{domain_name}': {e}")
        raise


def get_all_domain_repositories():
    active_domains = settings.CHATBOT_CONFIG.get('ACTIVE_DOMAINS', ['wine'])
    repositories = {}
    
    for domain_name in active_domains:
        repositories[domain_name] = get_domain_repository(domain_name)
    
    return repositories
