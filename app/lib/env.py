from dotenv import load_dotenv
import os


load_dotenv()


class EnvVars:
    """
    Singleton class for loading env_vars to use in the whole app \nUsage : _instance.{env_name}
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EnvVars, cls).__new__(cls)
            cls._instance._load_vars()
        return cls._instance

    def _load_vars(self):
        self.DB_URI = os.getenv("DB_URI")


env_loader = EnvVars()


print(env_loader.DB_URI)
