"""Hamroh — application factory.

`create_app()` loads config, runs migrations, registers blueprints and imports
the hook modules so their `@on(...)` decorators fire. Adding a hook means
adding a filename to HOOK_MODULES; adding an endpoint means adding a blueprint.
"""

import importlib
import logging

from flask import Flask

from config import Config, features
from core import db
from core.errors import register_error_handlers
from core.responses import ok

# Extension modules imported for their side effects (decorator registration).
# A new hook/analyzer/notifier = a new file listed here, nothing else changes.
HOOK_MODULES = []
ANALYZER_MODULES = []
NOTIFIER_MODULES = []

# (import path, url_prefix or None)
BLUEPRINTS = [
    ("routes.demo_api:bp", "/api/v1/demo"),
]


def _load_modules(app, names, kind):
    for name in names:
        try:
            importlib.import_module(name)
            app.logger.info("%s loaded: %s", kind, name)
        except Exception:
            # A broken optional extension must not stop the app from starting.
            app.logger.exception("%s failed to load: %s", kind, name)


def _register_blueprints(app):
    for import_path, url_prefix in BLUEPRINTS:
        module_name, _, attr = import_path.rpartition(":")
        module = importlib.import_module(module_name)
        blueprint = getattr(module, attr)
        app.register_blueprint(blueprint, url_prefix=url_prefix)
        app.logger.info("blueprint registered: %s", import_path)


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    logging.basicConfig(
        level=logging.DEBUG if app.config.get("DEBUG") else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    db.init_app(app)  # teardown + run_migrations()

    _load_modules(app, ANALYZER_MODULES, "analyzer")
    _load_modules(app, NOTIFIER_MODULES, "notifier")
    _load_modules(app, HOOK_MODULES, "hook")

    _register_blueprints(app)
    register_error_handlers(app)

    @app.get("/health")
    def health():
        return ok({
            "status": "ok",
            "db": app.config["DB_PATH"],
            "features": features.as_dict(),
        })

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=app.config["HOST"],
        port=app.config["PORT"],
        debug=app.config["DEBUG"],
    )
