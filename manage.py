
#!/usr/bin/env python
import os
import sys
import logging

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        logger.info("Starting Django application...")
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "health_check.settings")
        try:
            from django.core.management import execute_from_command_line
        except ImportError as exc:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed?"
            ) from exc
        
        # Display some helpful information
        if len(sys.argv) > 1:
            if sys.argv[1] in ['runserver', 'migrate', 'makemigrations']:
                logger.info(f"Running command: {' '.join(sys.argv[1:])}")
        
        # Execute the command
        execute_from_command_line(sys.argv)
        
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        sys.exit(1)
