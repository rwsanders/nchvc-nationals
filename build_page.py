"""Build the viewer page from page_template.html.

python build_page.py                       data.json      -> nchvc_nationals.html (data embedded, for a Claude artifact)
python build_page.py demo_data.json demo   demo data      -> nchvc_demo.html (embedded, with DEMO banner)
python build_page.py --site                -> site/ (index.html loads data.json live; demo.html; Azure SWA config)
"""
import json, os, shutil, sys

here = os.path.dirname(os.path.abspath(__file__))
tpl = open(os.path.join(here, "page_template.html"), encoding="utf-8").read()
DEMO_BANNER = ('<div style="background:var(--live);color:var(--surface);text-align:center;padding:8px 16px;'
               'font-weight:700;letter-spacing:.04em">DEMO: made-up scores to preview how results will look. '
               'Not real results.</div>')
SWA_CONFIG = {
    "routes": [{"route": "/data.json", "headers": {"Cache-Control": "no-cache, max-age=0"}}],
    "globalHeaders": {"X-Content-Type-Options": "nosniff"},
    "mimeTypes": {".json": "application/json"},
}


def render(data, demo=False):
    blob = "null" if data is None else json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", r"<\/")
    page = tpl.replace("__DATA__", blob)
    if demo:
        page = page.replace("<title>NCHVC Nationals 2026</title>", "<title>NCHVC Nationals Demo</title>")
        page = page.replace("<!--BANNER-->", DEMO_BANNER)
    # the artifact host adds the document skeleton; a standalone site needs its own
    return page


def standalone(page):
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            '<style>[hidden]{display:none!important} body{margin:0} img{max-width:100%}</style>\n'
            '</head>\n<body>\n' + page + '\n</body>\n</html>\n')


def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print("wrote", path, os.path.getsize(path) // 1024, "KB")


def load(name):
    return json.load(open(os.path.join(here, name), encoding="utf-8"))


if "--site" in sys.argv:
    site = os.path.join(here, "site")
    shutil.rmtree(site, ignore_errors=True)
    os.makedirs(site)
    write(os.path.join(site, "index.html"), standalone(render(None)))
    shutil.copy(os.path.join(here, "data.json"), os.path.join(site, "data.json"))
    if os.path.exists(os.path.join(here, "demo_data.json")):
        write(os.path.join(site, "demo.html"), standalone(render(load("demo_data.json"), demo=True)))
    write(os.path.join(site, "staticwebapp.config.json"), json.dumps(SWA_CONFIG, indent=2))
else:
    src = sys.argv[1] if len(sys.argv) > 1 else "data.json"
    demo = len(sys.argv) > 2 and sys.argv[2] == "demo"
    write(os.path.join(here, "nchvc_demo.html" if demo else "nchvc_nationals.html"), render(load(src), demo))
