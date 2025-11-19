from odoo import http
from odoo.http import request


class PosReferralController(http.Controller):

    @http.route('/pos_referral/check_code', type='json', auth='public', methods=['POST'])
    def check_referral_code(self, code):
        """Check if referral code is valid"""
        referral = request.env['pos.referral.code'].sudo().search([('code', '=', code)], limit=1)

        if not referral:
            return {'valid': False, 'message': 'Referral code not found'}

        is_valid, message = referral.is_code_valid()
        return {
            'valid': is_valid,
            'message': message,
            'customer_name': referral.customer_id.name,
        }