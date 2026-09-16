from django.apps import AppConfig


class ChatbotConfig(AppConfig):
    
    default_auto_field = 'django.db.models.AutoField'
    name = 'chatbot'
    verbose_name = 'Chatbot Assistente'
    
    def ready(self):
        """Initialize chatbot when Django starts."""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("=" * 60)
        logger.info("CHATBOT APP READY - LOADING DOMAINS")
        logger.info("=" * 60)
        
        try:
            # Load tools from active domains
            from chatbot.core.tool_registry import get_tool_registry
            from chatbot.core.domain_loader import load_active_domains
            from django.conf import settings
            
            logger.info(f"Active domains: {settings.CHATBOT_CONFIG.get('ACTIVE_DOMAINS')}")
            
            registry = get_tool_registry()
            load_active_domains(registry)
            
            tools = registry.get_all_tools()
            logger.info(f"Successfully loaded {len(tools)} tools:")
            for tool in tools:
                logger.info(f"  - {tool.name}")
            
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"FAILED TO LOAD CHATBOT: {e}", exc_info=True)
            raise
