from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    # For code generation
    referral_code_generated = fields.Char(string='Generated Referral Code')
    referral_code_id = fields.Many2one('pos.referral.code', string='Referral Code Record')

    # For code usage
    used_referral_code = fields.Char(string='Used Referral Code')
    referral_discount = fields.Float(string='Referral Discount', default=0.0)
    referral_reward_created = fields.Boolean(string='Reward Created', default=False)

    @api.model
    def create_referral_code(self, customer_id, phone, order_id=False):
        """Create new referral code for customer"""
        referral_model = self.env['pos.referral.code']
        config = self.env['pos.config'].search([], limit=1)

        # Generate unique code
        code = referral_model.generate_unique_code(config.referral_code_prefix)

        # Create referral record
        referral_vals = {
            'code': code,
            'customer_id': customer_id,
            'phone_number': phone,
            'max_uses': config.max_uses_per_code,
        }

        if order_id:
            referral_vals['order_id'] = order_id

        referral = referral_model.create(referral_vals)

        return code, referral.id

    def apply_referral_discount(self, referral_code, order_amount):
        """Apply discount using referral code"""
        referral = self.env['pos.referral.code'].search([('code', '=', referral_code)], limit=1)

        if not referral:
            return False, "Referral code not found"

        # Validate code
        is_valid, message = referral.is_code_valid()
        if not is_valid:
            return False, message

        # Calculate discount
        config = self.env['pos.config'].search([], limit=1)
        discount_amount = (order_amount * config.referred_percentage) / 100

        # Apply discount and mark code used
        referral.mark_code_used(self, discount_amount)

        # Create reward for referrer
        self.create_reward_for_referrer(referral_code, discount_amount)

        return True, discount_amount

    def create_reward_for_referrer(self, referral_code, discount_amount):
        """Create reward for the referrer"""
        referral = self.env['pos.referral.code'].search([('code', '=', referral_code)], limit=1)

        if referral and not self.referral_reward_created:
            config = self.env['pos.config'].search([], limit=1)
            if config.referred_percentage > 0:
                reward_amount = (discount_amount * config.referrer_percentage) / config.referred_percentage

                # You can extend this to create actual rewards like:
                # - Loyalty points
                # - Coupons
                # - Credit notes

                self.referral_reward_created = True
                return reward_amount
        return 0

    @api.model
    def _order_fields(self, ui_order):
        """Override to include referral fields"""
        fields = super(PosOrder, self)._order_fields(ui_order)

        fields.update({
            'referral_code_generated': ui_order.get('referral_code_generated', False),
            'referral_code_id': ui_order.get('referral_code_id', False),
            'used_referral_code': ui_order.get('used_referral_code', False),
            'referral_discount': ui_order.get('referral_discount', 0.0),
        })

        return fields