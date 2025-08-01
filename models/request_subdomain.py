from email.policy import default
from tokenize import String

from odoo import fields, models, api
import time,os

class RequestSubdomain(models.Model):
    _name = 'request_subdomain.requestsubdomain'
    _description = 'Description'

    name = fields.Char(string="Name")
    email = fields.Char(string = "email")
    subdomain = fields.Char(string="Subdomain", size=10)
    module_ids = fields.Many2many('ir.module.module', string="Select Modules")
    is_active = fields.Boolean(string="Is active")
    is_stop = fields.Boolean(string="Is stop")
    status = fields.Selection([
        ('draft','Draft'),
        ('active','Active'),
        ('stopped','Stopped'),
    ],
        String='Status',
        default='draft'
    )

    def action_accept(self):
        for record in self:
            compose_filename = f"/opt/odoo-on-docker/{record.subdomain}-compose.yml"

            module_names = ','.join(
                ['{}'.format(name) for name in record.module_ids.mapped('name')]
            )

            yaml_content = f"""\
services:
  odoo-{record.subdomain}:
    image: odoo:18
    container_name: {record.subdomain}-container
    volumes:
      - /opt/odoo/server/odoo_18.0+e/odoo/addons:/mnt/odoo-18-ee
      - /opt/odoo/custom-addons/odoo-18ee-custom-addons:/mnt/extra-addons
      - ./conf/{record.subdomain}.conf:/etc/odoo/odoo.conf
    command: >
      odoo -d {record.subdomain}-db -i base,{module_names}
    networks:
      - odoo-net

networks:
  odoo-net:
    external: true
    """
            conf_filename=f"/opt/odoo-on-docker/conf/{record.subdomain}.conf"
            conf_content=f"""\
[options]
admin_passwd = admin-12321
db_host = db
db_port = 5432
db_user = shamim
db_password = shamim
addons_path = /mnt/odoo-18-ee,/mnt/extra-addons
db_filter = ^{record.subdomain}-db
"""
            caddyfile_path = "/opt/odoo-on-docker/Caddyfile"
            caddy_entry = f"""
{record.subdomain}.myodootest.space {{
    reverse_proxy odoo-{record.subdomain}:8069
    encode gzip
}}\n
"""
            with open(compose_filename, 'w') as f:
                f.write(yaml_content)
            with open(conf_filename,'w') as f:
                f.write(conf_content)
            with open(caddyfile_path, 'a') as f:
                f.write(caddy_entry)


            record.is_active=True
            record.is_stop=False
            record.status='active'
        return {'type': 'ir.actions.act_window_close'}

    def action_decline(self):
        for rec in self:
            subdomain = rec.subdomain

            # Define file paths
            yml_path = f"/opt/odoo-on-docker/{subdomain}-compose.yml"
            conf_path = f"/opt/odoo-on-docker/conf/{subdomain}.conf"
            caddyfile_path = "/opt/odoo-on-docker/Caddyfile"

            # Delete .yml file if exists
            if os.path.exists(yml_path):
                os.remove(yml_path)

            # Delete .conf file if exists
            if os.path.exists(conf_path):
                os.remove(conf_path)

            # Remove the subdomain block from the Caddyfile
            if os.path.exists(caddyfile_path):
                with open(caddyfile_path, "r") as file:
                    lines = file.readlines()

                new_lines = []
                inside_block = False

                for line in lines:
                    # Detect start of subdomain block
                    if subdomain in line:
                        inside_block = True
                        continue

                    # End of block detected
                    if inside_block and line.strip() == "}":
                        inside_block = False
                        continue

                    # If not inside the subdomain block, keep the line
                    if not inside_block:
                        new_lines.append(line)

                # Overwrite the Caddyfile
                with open(caddyfile_path, "w") as file:
                    file.writelines(new_lines)

        # Delete the record
        self.unlink()

        # Reload client UI
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {
                'model': 'request_subdomain.requestsubdomain',
                'view_mode': 'list,form',
            }
        }

    # def action_decline(self):
    #     # logic for declining the subdomain
    #     super().unlink()
    #     # return {
    #     #     'type': 'ir.actions.act_window',
    #     #     'name': 'Subdomain Request',
    #     #     'view_mode': 'list',
    #     #     'res_model': 'request_subdomain.requestsubdomain',
    #     #     'target': 'current',
    #     #     'tag':'reload'
    #     # }
    #
    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'reload',  # Reloads the view to reflect the unlinked record
    #         'params': {
    #             'model': 'request_subdomain.requestsubdomain',
    #             'view_mode': 'list,form',
    #         }
    #     }
    #     # return False

    def action_stop(self):
        for record in self:
            file_path="/opt/odoo-on-docker/stop.txt"
            with open(file_path,'a') as f:
                f.write(f"{record.subdomain}\n")

            self.status="stopped"

    def action_start(self):
        for record in self:
            file_path="/opt/odoo-on-docker/start.txt"
            with open(file_path,'a') as f:
                f.write(f"{record.subdomain}\n")

            self.status="active"

