from email.policy import default
from tokenize import String
import datetime
from odoo import fields, models, api,_
import time, os
from odoo.exceptions import ValidationError
from odoo.addons.test_convert.tests.test_env import record


class RequestSubdomain(models.Model):
    _name = 'request_subdomain.requestsubdomain'
    _description = 'Description'

    name = fields.Char(string="Name")
    email = fields.Char(string="email")
    subdomain = fields.Char(string="Subdomain", size=10)
    module_ids = fields.Many2many('ir.module.module', string="Select Modules")
    is_active = fields.Boolean(string="Is active")
    is_stop = fields.Boolean(string="Is stop")
    stop_time = fields.Datetime(compute="_compute_end_time", store=True)
    approved_date = fields.Datetime(string="Date when request approved")
    # total_duration = fields.Integer(string="Total Duration of the service")
    total_duration = fields.Selection([
        ('3','3 Hours'),
        ('month','1 Month'),
        ('year','1 Year'),
    ],
        String="Total Duration of the service",
        default='3',
    )
    status = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('stopped', 'Stopped'),
    ],
        String='Status',
        default='draft'
    )
    version = fields.Selection([
        ('18', '18'),
        ('17', '17'),
        ('16', '16'),
    ],
        String='Version',
        default='18',
    )
    edition = fields.Selection([
        ('enterprise', 'Enterprise'),
        ('community', 'Community'),
    ],
        String='Edition',
        default='enterprise'
    )

    @api.depends("total_duration")
    def _compute_end_time(self):
        now_utc = fields.Datetime.now()
        for value in self:
            if value.status != "draft":
                now_utc = value.approved_date
            temp_duration=3
            if value.total_duration=="3":
                temp_duration=3
            elif value.total_duration=="month":
                temp_duration=30*24
            else:
                temp_duration=365*24
            value.stop_time=now_utc + datetime.timedelta(hours=temp_duration)

    @api.model
    def corn_check_stop_time(self):
        """This method is called by cron to stop services whose stop_time has passed."""
        now_utc = fields.Datetime.now()
        record_to_stop = self.search([
            ('stop_time', '<=', now_utc),
            ('status','=', 'active')
        ])

        for record in record_to_stop:
            record.action_stop()

    def action_accept(self):
        for record in self:
            ent_path_18 = self.env['ir.config_parameter'].sudo().get_param(
                'request_subdomain.ent_path_18'
            )
            ent_path_17 = self.env['ir.config_parameter'].sudo().get_param(
                'request_subdomain.ent_path_17'
            )
            ent_path_16 = self.env['ir.config_parameter'].sudo().get_param(
                'request_subdomain.ent_path_16'
            )
            volumes_ent_temp=""
            if record.version=="18":
                if not ent_path_18:
                    raise ValidationError(_("Enterprise 18 path is not defined. Set Enterprise path from settings."))

                volumes_ent_temp=ent_path_18
            elif record.version=='17':
                if not ent_path_17:
                    raise ValidationError(_("Enterprise 17 path is not defined. Set Enterprise path from settings."))
                volumes_ent_temp=ent_path_17
            else:
                if not ent_path_16:
                    raise ValidationError(_("Enterprise 16 path is not defined. Set Enterprise path from settings."))
                volumes_ent_temp=ent_path_16

            compose_filename = f"/opt/odoo-on-docker/{record.subdomain}-compose.yml"
            volumes_enterprise = f"- {volumes_ent_temp}:/mnt/odoo-{record.version}-ee"
            volumes_enterprise_custom = f"- /opt/odoo/custom-addons/odoo-{record.version}ee-custom-addons:/mnt/extra-addons"
            volumes_community_custom = f"- /opt/odoo/custom-addons/odoo-{record.version}ce-custom-addons:/mnt/extra-addons"
            addons_path_enterprise = f"/mnt/odoo-{record.version}-ee,/mnt/extra-addons"
            addons_path_community = f"/mnt/extra-addons"
            domain_name= self.env['ir.config_parameter'].sudo().get_param(
                'request_subdomain.domain_name'
            )
            if not domain_name:
                raise ValidationError(_("Set Domain Name in settings"))

            module_names = ','.join(
                ['{}'.format(name) for name in record.module_ids.mapped('name')]
            )
            if record.version == '17':
                pass
            yaml_content = f"""\
services:
  odoo-{record.subdomain}:
    image: odoo:{record.version}
    container_name: {record.subdomain}-container
    volumes:
      {volumes_enterprise if record.edition == "enterprise" else ""}
      {volumes_enterprise_custom if record.edition == "enterprise" else volumes_community_custom}
      - ./conf/{record.subdomain}.conf:/etc/odoo/odoo.conf
      - /opt/odoo-on-docker:/opt/odoo-on-docker/
    command: >
      odoo -d {record.subdomain}-db -i {module_names}
    networks:
      - odoo-net

networks:
  odoo-net:
    external: true
volumes:
  odoo_db_data:
    """
            conf_filename = f"/opt/odoo-on-docker/conf/{record.subdomain}.conf"
            conf_content = f"""\
[options]
admin_passwd = admin-12321
db_host = db
db_port = 5432
db_user = shamim
db_password = shamim
addons_path = {addons_path_enterprise if record.edition == "enterprise" else addons_path_community}
db_filter = ^{record.subdomain}-db
"""
            caddyfile_path = "/opt/odoo-on-docker/Caddyfile"
            caddy_entry = f"""
{record.subdomain}.{domain_name} {{
    reverse_proxy odoo-{record.subdomain}:8069
    encode gzip
}}\n
"""
            with open(compose_filename, 'w') as f:
                f.write(yaml_content)
            with open(conf_filename, 'w') as f:
                f.write(conf_content)
            with open(caddyfile_path, 'a') as f:
                f.write(caddy_entry)

            record.is_active = True
            record.is_stop = False
            record.status = 'active'

            template = self.env.ref('request_subdomain.subdomain_request_accept')
            mail_server = self.env['ir.mail_server'].sudo().search([], limit=1)
            email_from = mail_server.smtp_user
            now_utc = datetime.datetime.now(datetime.UTC)
            send_time = now_utc + datetime.timedelta(minutes=10)
            url = f"https://{record.subdomain}.{domain_name}"
            if template:
                try:
                    email_values = {
                        'email_to': record.email,
                        'email_from': email_from,
                        'scheduled_date': send_time,
                        'auto_delete': False,
                    }
                    ctx = {
                        'default_model': 'request_subdomain.requestsubdomain',
                        'default_res_id': 1,
                        'default_email_to': record.email,  # Ensure the email field exists
                        'default_template_id': template.id,
                        'subdomain': record.subdomain,
                        'version': record.version,
                        'edition': record.edition,
                        'url': url,
                    }
                    s = template.with_context(**ctx).sudo().send_mail(self.id,email_values=email_values)
                except Exception as e:
                    pass
            record.approved_date=fields.datetime.now()
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

    def action_stop(self):
        for record in self:
            file_path = "/opt/odoo-on-docker/stop.txt"
            with open(file_path, 'a') as f:
                f.write(f"{record.subdomain}\n")

            self.status = "stopped"
            template = self.env.ref('request_subdomain.subdomain_service_stop')
            mail_server = self.env['ir.mail_server'].sudo().search([], limit=1)
            email_from = mail_server.smtp_user
            domain_name = self.env['ir.config_parameter'].sudo().get_param(
                'request_subdomain.domain_name'
            )
            url = f"https://{record.subdomain}.{domain_name}"
            if template:
                try:
                    email_values={
                        'email_from':email_from,
                        'email_to':record.email,
                        'auto_delete': False,
                    }
                    ctx = {
                        'default_model': 'request_subdomain.requestsubdomain',
                        'default_res_id': 1,
                        'default_email_to': record.email,  # Ensure the email field exists
                        'default_template_id': template.id,
                        'subdomain': record.subdomain,
                        'version': record.version,
                        'edition': record.edition,
                    }
                    s = template.with_context(**ctx).sudo().send_mail(self.id,email_values=email_values,force_send=True)
                except Exception as e:
                    pass

    def action_start(self):
        for record in self:
            file_path = "/opt/odoo-on-docker/start.txt"
            with open(file_path, 'a') as f:
                f.write(f"{record.subdomain}\n")

            self.status = "active"
            template = self.env.ref('request_subdomain.subdomain_service_restart')
            mail_server = self.env['ir.mail_server'].sudo().search([], limit=1)
            email_from = mail_server.smtp_user
            domain_name = self.env['ir.config_parameter'].sudo().get_param(
                'request_subdomain.domain_name'
            )
            url = f"https://{record.subdomain}.{domain_name}"
            if template:
                try:
                    email_values = {
                        'email_from': email_from,
                        'email_to': record.email,
                    }
                    ctx = {
                        'default_model': 'request_subdomain.requestsubdomain',
                        'default_res_id': 1,
                        'default_email_to': record.email,  # Ensure the email field exists
                        'default_template_id': template.id,
                        'subdomain': record.subdomain,
                        'version': record.version,
                        'edition': record.edition,
                        'auto_delete': False,
                        'url': url,
                    }
                    s = template.with_context(**ctx).sudo().send_mail(self.id, email_values=email_values,
                                                                      force_send=True)
                except Exception as e:
                    pass
    @api.model_create_multi
    def create(self, vals_list):
        record = self.browse()
        for vals in vals_list:
            # Ensure subdomain is lowercase or uppercase as needed
            if 'subdomain' in vals and vals['subdomain']:
                vals['subdomain'] = vals['subdomain'].lower()  # or .upper() if you prefer

            # Ensure name is capitalized
            if 'name' in vals and vals['name']:
                vals['name'] = vals['name'].title()

            # Set default status to 'draft' if not provided
            if 'status' not in vals:
                vals['status'] = 'draft'
            record = super(RequestSubdomain, self).create(vals)
            approval_process = self.env['ir.config_parameter'].sudo().get_param(
                'request_subdomain.approval_process'
            )

            if not approval_process:
                record.action_accept()

        return record
