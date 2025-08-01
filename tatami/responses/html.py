
from jinja2 import Environment, FileSystemLoader
from starlette.responses import HTMLResponse


class TemplateResponse(HTMLResponse):
    def __init__(self, template_name: str, content = None, status_code = 200, headers = None, media_type = None, background = None):
        environment = Environment(loader=FileSystemLoader('templates'))
        template = environment.get_template(template_name)
        super().__init__(template.render(content), status_code, headers, media_type, background)