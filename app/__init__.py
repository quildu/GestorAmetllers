import os

from flask import Flask

from .auth import login_manager
from .paths import resource_path
from .services.catalog import seed_data


def create_app():
    app = Flask(
        __name__,
        template_folder=resource_path("templates"),
        static_folder=resource_path("static"),
    )
    app.secret_key = os.getenv("SECRET_KEY", "dev-key-canvia-en-produccio")
    app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25MB per petició (varis fitxers)
    login_manager.init_app(app)

    from .web import (
        hooks,
        template_filters,
        auth_routes,
        parcel_routes,
        labor_routes,
        production_routes,
        expense_routes,
        history_routes,
        master_data_routes,
        document_routes,
        vegga_routes,
        report_routes,
    )

    for module in (
        hooks,
        template_filters,
        auth_routes,
        parcel_routes,
        labor_routes,
        production_routes,
        expense_routes,
        history_routes,
        master_data_routes,
        document_routes,
        vegga_routes,
        report_routes,
    ):
        module.register(app)

    return app


__all__ = ["create_app", "seed_data"]
