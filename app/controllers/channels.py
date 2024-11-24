import app.models.model_types as model_type
import app.utils.mongo_utils as mongo_utils
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader('app/files'))

async def ast_info(ast_id):
    ast_data = mongo_utils.fetch_channel_info_by_ast_id(ast_id)
    return ast_data

async def api_integration(channel: model_type.Channel):
    template = env.get_template('api_template.txt')
    api_data = template.render(api_token=channel.apiToken, agent_name=channel.astName)
    return api_data