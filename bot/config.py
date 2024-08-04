import yaml
import os
from dotenv import load_dotenv

# configuration
load_dotenv()

# read YML files
def read_yaml(file_path):
    """Utility function to read YAML configuration files."""
    with open(file_path, 'r', encoding="utf8") as file:
        return yaml.safe_load(file)

# paths to config files
CONFIG_PATHS = {
    "config": "config/config.yml",
    "models": "config/models.yml",
    "premium_groups": "config/premium_groups.yml",
    "group_settings_desc": "config/group_settings_desc.yml"
}

# Loading configuration data from YAML files
config_data = read_yaml(CONFIG_PATHS["config"])
models = read_yaml(CONFIG_PATHS["models"])
premium_groups = read_yaml(CONFIG_PATHS["premium_groups"])
group_settings_mapping = read_yaml(CONFIG_PATHS["group_settings_desc"])


# TEST & PROD environments
class Config:
    """Base configuration class with default settings."""
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'prod')

class ProductionConfig(Config):
    """Production specific configuration."""
    MONGO_DB_CONNECTION_STRING = os.getenv('MONGO_DB_CONNECTION_STRING')
    GUARDY_BOT_API_KEY = os.getenv('GUARDY_BOT_API_KEY')
    GUARDY_URL = os.getenv('GUARDY_URL')
    GUARDY_ID = os.getenv('GUARDY_ID')
    GUARDY_USERNAME = os.getenv('GUARDY_USERNAME')
    OPENAI_GUARDY_ASSISTANT_ID = os.getenv('OPENAI_GUARDY_ASSISTANT_ID')
    OPENAI_GUARDY_ASSISTANT_API_KEY = os.getenv('OPENAI_GUARDY_ASSISTANT_API_KEY')

class TestingConfig(Config):
    """Testing specific configuration."""
    MONGO_DB_CONNECTION_STRING = os.getenv('MONGO_DB_CONNECTION_STRING')
    GUARDY_BOT_API_KEY = os.getenv('GUARDY_TEST_BOT_API_KEY')
    GUARDY_URL = os.getenv('GUARDY_DEV_URL')
    GUARDY_ID = os.getenv('GUARDY_DEV_ID')
    GUARDY_USERNAME = os.getenv('GUARDY_DEV_USERNAME')
    OPENAI_GUARDY_ASSISTANT_ID = os.getenv('OPENAI_GUARDY_ASSISTANT_ID')
    OPENAI_GUARDY_ASSISTANT_API_KEY = os.getenv('OPENAI_GUARDY_ASSISTANT_API_KEY')

def get_config():
    """Get the appropriate configuration class based on the environment setting."""
    if Config.ENVIRONMENT == 'test':
        return TestingConfig()
    elif Config.ENVIRONMENT == "prod":
        return ProductionConfig()
    else:
        raise EnvironmentError("ENVIRONMENT not found or is not correctly set.")

# Example usage:
# config = get_config()
