# -*- coding: utf-8 -*-
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

        return request.redirect('/my/request_subdomain')
