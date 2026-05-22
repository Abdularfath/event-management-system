import importlib.util
import os

spec = importlib.util.spec_from_file_location("main_app", os.path.join(os.path.dirname(__file__), "app.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
application = module.app

if __name__ == "__main__":
    application.run()
