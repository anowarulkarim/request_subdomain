from odoo import fields, models, api
import subprocess,time,os

class RequestSubdomain(models.Model):
    _name = 'request_subdomain.requestsubdomain'
    _description = 'Description'

    name = fields.Char(string="Name")
    email = fields.Char(string = "email")
    subdomain = fields.Char(string="Subdomain", size=10)
    module_ids = fields.Many2many('ir.module.module', string="Select Modules")

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

            time.sleep(2)

            # Optional: check if file truly exists before running docker-compose
            if not os.path.exists(compose_filename):
                raise FileNotFoundError(f"{compose_filename} not found")
            command=f"docker-compose -f {compose_filename} up"
            subprocess.run(command,shell=True)

        return {'type': 'ir.actions.act_window_close'}

    def action_decline(self):
        # logic for declining the subdomain
        return {'type': 'ir.actions.act_window_close'}
