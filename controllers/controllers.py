# -*- coding: utf-8 -*-
import re

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
import random
import datetime
from odoo import http, fields, _
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.http import request
from math import ceil
from itertools import groupby as groupbyelem
import base64

class RequestSubdomain(http.Controller):
    @http.route('/my/request_subdomain',type='http', auth='public',website=True)
    def index(self):
        if not request.session.get('otp_email'):
            return request.redirect('/request_subdomain/create/otp')
        modules = request.env['ir.module.module'].sudo().search([])
        ctx = {
            'frontend_languages': [{'code': 'en_US', 'name': 'English'}],
            'modules': modules,
            'page_name': 'requesting_subdomain',
            'email': request.session.get('otp_email')
        }
        return request.render('request_subdomain.portal_request_subdomain',ctx)

    @http.route(['/my/request-subdomain/submit'], type='http', auth="public", website=True, csrf=True)
    def submit_request_subdomain(self, **post):
        name = post.get('name')
        email = post.get('email')
        subdomain = post.get('subdomain')
        version = post.get('version')
        edition = post.get('edition')
        selected_modules = request.httprequest.form.getlist('module_ids')

        # Create the record
        record = request.env['request_subdomain.requestsubdomain'].sudo().create({
            'name': name,
            'email': email,
            'subdomain': subdomain,
            'version': version,
            'edition': edition,
            'module_ids': [
                (6, 0, request.env['ir.module.module'].sudo().search([('name', 'in', selected_modules)]).ids)]
        })
        del request.session['otp_email']
        return request.redirect('/request-subdomain/thank-you')

    @http.route('/check-subdomains', type='json', auth='public', csrf=False)
    def check_subdomains(self):
        subdomains = []
        try:
            with open('/opt/odoo-on-docker/Caddyfile', 'r') as f:
                content = f.read()
                subdomains = re.findall(r'(\w+)\.myodootest\.space', content)
        except Exception as e:
            return {'error': str(e)}
        return {'subdomains': list(set(subdomains))}

    @http.route('/my/subdomains', type='http', auth='user', website=True)
    def portal_subdomains(self, **kw):
        subdomains = []
        try:
            with open('/opt/odoo-on-docker/Caddyfile', 'r') as f:
                content = f.read()
                # Match full domain like abc.myodootest.space
                subdomains = re.findall(r'(\w+\.myodootest\.space)', content)
                subdomains = list(set(subdomains))  # Remove duplicates
        except Exception as e:
            subdomains = ['Error: ' + str(e)]

        return request.render('request_subdomain.subdomain_list', {
            'subdomains': subdomains,
            'page_name':'subdomain_list',
        })

    @http.route(['/request-subdomain/thank-you', '/my/request-subdomain/thank-you'], type='http', auth='public',
                website=True)
    def request_thankyou(self, **kw):
        return request.render('request_subdomain.portal_request_thankyou')

    @http.route('/request_subdomain/create/otp', auth='public', website=True, methods=['POST'], csrf=False)
    def send_otp(self, **post):
        """Generate OTP and store email in session"""
        email = post.get('email')

        if not email:
            return http.Response('{"status": "error", "message": "Email is required"}', content_type='application/json')

        # Generate OTP
        otp_code = str(random.randint(100000, 999999))
        expiry_time = datetime.datetime.now() + datetime.timedelta(minutes=5)

        # Remove previous OTPs
        request.env['subotp.varification'].sudo().search([('email', '=', email)]).unlink()


        # Store OTP in database
        x = request.env['subotp.varification'].sudo().create({
            'email': email,
            'otp': otp_code,
            'expiry_time': expiry_time,
            'verified': False
        })
        template = request.env.ref('request_subdomain.otp_verification_template')
        mail_server = request.env['ir.mail_server'].sudo().search([],limit=1)
        email_from = mail_server.smtp_user
        # now_utc = datetime.datetime.now(datetime.UTC)
        # send_time = now_utc + datetime.timedelta(minutes=10)
        if template:
            try:
                # Add context with force_send to ensure immediate email sending
                email_values = {
                    'email_to': email,
                    'email_from': email_from,
                }

                ctx = {
                    'default_model': 'subotp.verification',
                    'default_res_id': 1,
                    'default_email_to': email,  # Ensure the email field exists
                    'default_template_id': template.id,
                    'otp_code': otp_code,
                }

                s = template.with_context(**ctx).sudo().send_mail(x, email_values=email_values)

            except Exception as e:
                pass

        return http.Response('{"status": "success", "message": "OTP has been sent"}', content_type='application/json')

    @http.route('/request_subdomain/create/otp', auth='public', website=True, methods=['GET'])
    def get_otp_template(self, **kwargs):
        """Render the OTP form template for user input"""
        return request.render('request_subdomain.view_email_input_form', {})

    @http.route('/request_subdomain/verify_otp', auth='public', website=True, methods=['POST'], csrf=False)
    def verify_otp(self, **post):
        """Verify OTP"""
        email = post.get('email')
        otp = post.get('otp')

        if not email or not otp:
            return http.Response('{"status": "error", "message": "Email and OTP are required"}',
                                 content_type='application/json')

        otp_record = request.env['subotp.varification'].sudo().search([('email', '=', email),('otp', '=', otp)], limit=1)

        if not otp_record or otp_record.expiry_time < datetime.datetime.now():
            return http.Response('{"status": "error", "message": "Invalid or expired OTP"}',
                                 content_type='application/json')
        # Mark OTP as verified
        otp_record.sudo().write({'verified': True})
        request.session['otp_email'] = email
        return http.Response('{"status": "success", "message": "OTP verified successfully"}',
                             content_type='application/json')