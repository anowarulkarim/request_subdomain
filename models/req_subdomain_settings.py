from odoo import models, fields, api
import os

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    approval_process = fields.Boolean(
        string="Need Approval Process",
        config_parameter='request_subdomain.approval_process',
    )
    domain_name = fields.Char(
        string="Domain Name",
        config_parameter='request_subdomain.domain_name',
    )
    ent_path_18 = fields.Char(
        string="odoo 18 enterprise path",
        config_parameter='request_subdomain.ent_path_18'
    )
    ent_path_17 = fields.Char(
        string="odoo 17 enterprise path",
        config_parameter='request_subdomain.ent_path_17'
    )
    ent_path_16 = fields.Char(
        string="odoo 16 enterprise path",
        config_parameter='request_subdomain.ent_path_16'
    )

    def add_domain_name(self):
        """
        Add the given domain name to the top of the Caddyfile,
        only if it doesn't already exist.
        """
        file_path = "/opt/odoo-on-docker/Caddyfile"

        domain = self.domain_name.strip() if self.domain_name else None
        if not domain:
            return

        new_block = f"""{domain} {{
    reverse_proxy odoo-admin-18ee:8069
    encode gzip
}}

"""

        # Read old content
        old_content = ""
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                old_content = f.read()

        # Check if domain already exists (at beginning of a line)
        lines = old_content.splitlines()
        for line in lines:
            if line.strip().startswith(domain):
                # Domain already exists → do nothing
                return

        # Prepend new block
        updated_content = new_block + old_content

        with open(file_path, "w") as f:
            f.write(updated_content)
