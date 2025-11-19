from odoo import models, fields, api


class ReferralSettings(models.Model):
    _name = 'referral.settings'
    _description = 'Referral Program Settings'

    name = fields.Char(string='Settings Name', default='Referral Settings', required=True)
    pos_config_id = fields.Many2one('pos.config', string='POS Configuration', required=True)
    referral_enabled = fields.Boolean(string='Enable Referral System', default=True)
    referrer_percentage = fields.Float(string='Referrer Reward %', default=15.0)
    referred_percentage = fields.Float(string='Referred Customer Discount %', default=10.0)
    referral_code_prefix = fields.Char(string='Code Prefix', default='REF-', size=10)
    min_order_amount = fields.Float(string='Minimum Order Amount', default=0.0)
    max_uses_per_code = fields.Integer(string='Max Uses Per Code', default=1)
    code_validity_days = fields.Integer(string='Code Validity (Days)', default=365)

    _sql_constraints = [
        ('pos_config_unique', 'unique(pos_config_id)', 'Referral settings already exist for this POS configuration!'),
    ]

    @api.model
    def get_settings(self, pos_config_id):
        """Get or create settings for a POS configuration"""
        settings = self.search([('pos_config_id', '=', pos_config_id)], limit=1)
        if not settings:
            settings = self.create({
                'name': f'Referral Settings - {pos_config_id}',
                'pos_config_id': pos_config_id,
            })
        return settings