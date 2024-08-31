import os
from pathlib import Path

import jinja2
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from barber.folder import Collection, Image
from barber.utils import config


HERE = Path(__file__).parent
cfg = config()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(
    directory=HERE / "templates", undefined=jinja2.StrictUndefined
)
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
def folder(request: Request, name: str, pos: int):
    resp = templates.TemplateResponse(
        request=request,
        name="folder.html",
        context={
            "folder": collection.folders[name][pos - 1],
        },
    )
    return resp


@app.get("/img/{digest}/{filename}", response_class=HTMLResponse)
def img(request: Request, digest: str, thumb: bool = False):
    # TODO handle file ext (jpg vs png)
    image = Image.get(digest)
    src = image.thumb() if thumb else image.full()
    response = StreamingResponse(src, media_type="image/jpeg")
    response.headers["Content-Disposition"] = f"inline; filename={image.path.name}"
    return response


@app.post("/star/{digest}/{filename}", response_class=HTMLResponse)
def star(request: Request, digest: str):
    image = Image.get(digest)
    value = image.flip_star()
    return "★" if value else "☆"


@app.get("/solo/{digest}/{filename}", response_class=HTMLResponse)
def solo(request: Request, digest: str):
    image = Image.get(digest)
    resp = templates.TemplateResponse(
        request=request,
        name="solo.html",
        context={
            "image": image,
        },
    )
    return resp
