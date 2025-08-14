from odoo import models, fields,api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    approval_process = fields.Boolean(
        string="Need Approval Process",
        config_parameter='request_subdomain.approval_process',
    )


