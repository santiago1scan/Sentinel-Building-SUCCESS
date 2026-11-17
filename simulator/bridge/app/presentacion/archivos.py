"""Archivos estáticos restringidos."""

from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles
from starlette.types import Scope


class SoloHojasYScripts(StaticFiles):
    """Sirve únicamente .css y .js. Las plantillas .html de la misma carpeta no se exponen."""

    async def get_response(self, path: str, scope: Scope):
        if not path.lower().endswith((".css", ".js")):
            raise HTTPException(status_code=404)
        return await super().get_response(path, scope)
