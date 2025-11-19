from odoo import models, fields, api
from odoo.exceptions import ValidationError
import random
import string
from datetime import datetime, timedelta


class PosReferralCode(models.Model):
    _name = 'pos.referral.code'
    _description = 'POS Referral Codes'
    _rec_name = 'code'

    code = fields.Char(string='Referral Code', required=True, index=True)
    customer_id = fields.Many2one('res.partner', string='Customer', required=True)
    order_id = fields.Many2one('pos.order', string='Generated in Order')
    issue_date = fields.Datetime(string='Issue Date', default=fields.Datetime.now)
    expiry_date = fields.Datetime(string='Expiry Date', compute='_compute_expiry_date', store=True)
    is_active = fields.Boolean(string='Active', default=True)
    phone_number = fields.Char(string='Phone Number', required=True)

    # Usage tracking
    used_count = fields.Integer(string='Times Used', default=0)
    max_uses = fields.Integer(string='Maximum Uses', default=1)
    total_discount_given = fields.Float(string='Total Discount Given', default=0.0)
    total_rewards_earned = fields.Float(string='Total Rewards Earned', default=0.0)

    # Relations to orders where this code was used
    used_order_ids = fields.Many2many('pos.order', string='Orders Where Used')

    @api.depends('issue_date')
    def _compute_expiry_date(self):
        """Compute expiry date based on POS config validity days"""
        for record in self:
            if record.issue_date:
                # Get the validity days from POS config
                config = self.env['pos.config'].search([], limit=1)
                validity_days = config.code_validity_days if config else 365
                record.expiry_date = record.issue_date + timedelta(days=validity_days)
            else:
                record.expiry_date = False

    @api.model
    def generate_unique_code(self, prefix="REF-"):
        """Generate unique referral code"""
        while True:
            # Generate 6 character alphanumeric code
            characters = string.ascii_uppercase + string.digits
            random_part = ''.join(random.choices(characters, k=6))
            new_code = f"{prefix}{random_part}"

            # Check if code exists
            if not self.search([('code', '=', new_code)]):
                return new_code

    def is_code_valid(self):
        """Check if code can be used"""
        self.ensure_one()

        # Check active status
        if not self.is_active:
            return False, "Code is not active"

        # Check expiry
        if self.expiry_date and self.expiry_date < fields.Datetime.now():
            return False, "Code has expired"

        # Check usage limit
        if self.max_uses > 0 and self.used_count >= self.max_uses:
            return False, "Code usage limit reached"

        return True, "Valid"

    def mark_code_used(self, order, discount_amount):
        """Mark code as used and update statistics"""
        self.ensure_one()
        self.write({
            'used_count': self.used_count + 1,
            'total_discount_given': self.total_discount_given + discount_amount,
            'used_order_ids': [(4, order.id)],
        })

        # Calculate and store reward for referrer
        config = self.env['pos.config'].search([], limit=1)
        if config.referred_percentage > 0:
            reward_amount = (discount_amount * config.referrer_percentage) / config.referred_percentage
            self.total_rewards_earned += reward_amount

        # Deactivate if reached max uses
        if self.max_uses > 0 and self.used_count >= self.max_uses:
            self.is_active = False

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Referral code must be unique!'),
    ]