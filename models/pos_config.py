from odoo import models, fields


class PosConfig(models.Model):
    _inherit = 'pos.config'

    # Keep only a simple field to indicate if referral system is available
    referral_system_available = fields.Boolean(string='Referral System Available',
                                               compute='_compute_referral_available')

    def _compute_referral_available(self):
        """Compute if referral system is available for this POS"""
        for record in self:
            record.referral_system_available = True