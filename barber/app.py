import os
import argparse
from io import BytesIO
from pathlib import Path

import uvicorn
import jinja2
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from barber.folder import Collection, Image
from barber.utils import load_config


HERE = Path(__file__).parent
cfg = load_config(Path(os.environ.get("BARBER_TOML", "./barber.toml")))

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory=HERE / "templates", undefined=jinja2.StrictUndefined)
collection = Collection()
for name, pattern in cfg["sources"].items():
    collection.add_source(name, pattern)


@app.get("/", response_class=HTMLResponse)
def read_item(request: Request):
    resp = templates.TemplateResponse(
        request=request, name="index.html", context={"collection": collection}
    )
    return resp


@app.get("/folder/{name}/{pos}", response_class=HTMLResponse)
def read_item(request: Request, name: str, pos: int):
    resp = templates.TemplateResponse(
        request=request,
        name="folder.html",
        context={
            "folder": collection.folders[name][pos - 1],
        },
    )
    return resp


@app.get("/thumb/{digest}", response_class=HTMLResponse)
def thumb(request: Request, digest: str):
    image = Image.get(digest)
    response = StreamingResponse(image.thumb(), media_type="image/jpeg")
    response.headers["Content-Disposition"] = f"inline; filename={image.path.name}"
    return response
