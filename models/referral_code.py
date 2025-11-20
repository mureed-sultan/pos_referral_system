from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import random
import string


class PosReferralCode(models.Model):
    _name = 'pos.referral.code'
    _description = 'POS Referral Code'
    _rec_name = 'code'

    code = fields.Char(string='Referral Code', required=True, index=True)
    customer_id = fields.Many2one('res.partner', string='Customer', required=True)
    phone_number = fields.Char(string='Phone Number')
    order_id = fields.Many2one('pos.order', string='Source Order')
    max_uses = fields.Integer(string='Maximum Uses', default=1)
    times_used = fields.Integer(string='Times Used', default=0)
    total_discount_given = fields.Float(string='Total Discount Given', default=0.0)
    created_date = fields.Datetime(string='Created Date', default=fields.Datetime.now)
    expiry_date = fields.Datetime(string='Expiry Date', compute='_compute_expiry_date', store=True)
    is_active = fields.Boolean(string='Active', default=True)
    pos_config_id = fields.Many2one('pos.config', string='POS Configuration', required=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Referral code must be unique!'),
    ]

    @api.depends('created_date')
    def _compute_expiry_date(self):
        """Compute expiry date based on settings validity days"""
        for record in self:
            if record.pos_config_id:
                config = self.env['referral.settings'].get_settings(record.pos_config_id.id)
                validity_days = config.code_validity_days if config else 365
            else:
                validity_days = 365

            if record.created_date:
                record.expiry_date = record.created_date + timedelta(days=validity_days)
            else:
                record.expiry_date = False

    @api.model
    def generate_unique_code(self, prefix="REF", customer_name=False):
        """Generate a unique referral code with customer name initials"""
        # Extract initials from customer name
        initials = ""
        if customer_name:
            # Clean the name: take first word, remove special chars, uppercase, max 3 chars
            name_parts = customer_name.split()
            if name_parts:
                first_name = name_parts[0]
                cleaned_name = ''.join(c for c in first_name if c.isalpha())[:3].upper()
                if cleaned_name:
                    initials = f"-{cleaned_name}"

        while True:
            # Generate random numbers
            random_numbers = ''.join(random.choices(string.digits, k=4))

            # Create code: prefix + initials + random numbers
            code = f"{prefix}{initials}-{random_numbers}".upper()

            # Check if code already exists
            if not self.search([('code', '=', code)], limit=1):
                return code

    def is_code_valid(self):
        """Check if referral code is valid"""
        self.ensure_one()

        if not self.is_active:
            return False, "Referral code is not active"

        if self.expiry_date and self.expiry_date < fields.Datetime.now():
            return False, "Referral code has expired"

        if self.times_used >= self.max_uses:
            return False, "Referral code has reached maximum uses"

        return True, "Valid code"

    def mark_code_used(self, discount_amount):
        """Mark code as used and update statistics - no order parameter needed"""
        print(f"🎯 MARK_CODE_USED: Code {self.code}, Discount: {discount_amount}")

        self.ensure_one()
        self.write({
            'times_used': self.times_used + 1,
            'total_discount_given': self.total_discount_given + discount_amount,
        })
        print(f"✅ Code updated - Times used: {self.times_used}, Total discount: {self.total_discount_given}")

    @api.constrains('max_uses')
    def _check_max_uses(self):
        for record in self:
            if record.max_uses < 1:
                raise ValidationError("Maximum uses must be at least 1")