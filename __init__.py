# -*- coding: utf-8 -*-

from . import controllers
from . import models



def post_init_hook(env):
    env['ir.config_parameter'].sudo().set_param('request_subdomain.approval_process', 'True')