import os
import argparse
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from barber.folder import Collection
from barber.utils import load_config


HERE = Path(__file__).parent
cfg = load_config(Path(os.environ.get("BARBER_TOML", "./barber.toml")))

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory=HERE / "templates")
collection = Collection()
for name, pattern in cfg["sources"].items():
    collection.add_source(name, pattern)

    
@app.get("/", response_class=HTMLResponse)
def read_item(request: Request):
    resp = templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"collection": collection}
    )
    return resp


@app.get("/img/{uuid}", response_class=HTMLResponse)
async def read_item(request: Request):
    memfile = BytesIO(attachment['content'])
    response = StreamingResponse(memfile, media_type=attachment['contentType'])
    response.headers["Content-Disposition"] = f"inline; filename={attachment['name']}"
        
