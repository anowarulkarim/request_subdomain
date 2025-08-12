# -*- coding: utf-8 -*-
import re

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class RequestSubdomain(http.Controller):
    @http.route('/my/request_subdomain',type='http', auth='public',website=True)
    def index(self):
        modules = request.env['ir.module.module'].sudo().search([])
        ctx = {
            'frontend_languages': [{'code': 'en_US', 'name': 'English'}],
            'modules': modules,
            'page_name': 'requesting_subdomain'
        }
        return request.render('request_subdomain.portal_request_subdomain',ctx)

    @http.route(['/my/request-subdomain/submit'], type='http', auth="public", website=True, csrf=True)
    def submit_request_subdomain(self, **post):
        name = post.get('name')
        email = post.get('email')
        subdomain = post.get('subdomain')
        selected_modules = request.httprequest.form.getlist('module_ids')

        # Create the record
        record = request.env['request_subdomain.requestsubdomain'].sudo().create({
            'name': name,
            'email': email,
            'subdomain': subdomain,
            'module_ids': [
                (6, 0, request.env['ir.module.module'].sudo().search([('name', 'in', selected_modules)]).ids)]
        })

        return request.redirect('/request-subdomain/thank-you')

        # return request.redirect('/my/request_subdomain')

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
