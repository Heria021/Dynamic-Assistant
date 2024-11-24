import app.models.model_types as model_type
import app.utils.mongo_utils as mongo_utils

async def ast_info(ast_id):
    ast_data = mongo_utils.fetch_channel_info_by_ast_id(ast_id)
    return ast_data
