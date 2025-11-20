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
    def create_referral_code(self, customer_id, phone, order_id=False, pos_config_id=False, customer_name=False):
        """Create new referral code for customer with customer name included"""
        referral_model = self.env['pos.referral.code']

        # Get settings for the current POS configuration
        if not pos_config_id:
            pos_config_id = self.env.context.get('pos_config_id') or self.env['pos.config'].search([], limit=1).id

        if not pos_config_id:
            raise ValidationError("No POS configuration found")

        config = self.env['referral.settings'].get_settings(pos_config_id)

        if not config.referral_enabled:
            raise ValidationError("Referral system is not enabled for this POS")

        # Generate unique code with customer name
        code = referral_model.generate_unique_code(config.referral_code_prefix, customer_name)

        # Create referral record
        referral_vals = {
            'code': code,
            'customer_id': customer_id,
            'phone_number': phone,
            'max_uses': config.max_uses_per_code,
            'pos_config_id': pos_config_id,
        }

        if order_id:
            referral_vals['order_id'] = order_id

        referral = referral_model.create(referral_vals)

        return {
            'code': code,
            'referral_id': referral.id
        }

    @api.model  # CHANGE: Add @api.model decorator to make it a model method
    def apply_referral_discount(self, referral_code, order_amount, pos_config_id=False):
        """Apply discount using referral code"""
        print("🔍 APPLY_REFERRAL_DISCOUNT CALLED:")
        print("   Referral Code:", repr(referral_code))
        print("   Order Amount:", order_amount)
        print("   POS Config ID:", pos_config_id)
        print("   Self (model):", self)  # This will now be the model, not a record

        # Search for referral code
        referral = self.env['pos.referral.code'].search([('code', '=', referral_code)], limit=1)
        print("   Referral Found:", referral.code if referral else "None")

        # Debug: Check all referral codes in database
        all_codes = self.env['pos.referral.code'].search([])
        print("   All referral codes in DB:", [code.code for code in all_codes])

        if not referral:
            return {
                'success': False,
                'message': f"Referral code '{referral_code}' not found"
            }

        # Get POS config from referral or parameter
        if not pos_config_id:
            pos_config_id = referral.pos_config_id.id or self.env['pos.config'].search([], limit=1).id
        print("   Using POS Config ID:", pos_config_id)

        config = self.env['referral.settings'].get_settings(pos_config_id)
        print("   Settings Found:", bool(config))
        print("   Referral Enabled:", config.referral_enabled if config else "No config")
        print("   Min Order Amount:", config.min_order_amount if config else "No config")
        print("   Referred Percentage:", config.referred_percentage if config else "No config")

        if not config.referral_enabled:
            return {
                'success': False,
                'message': "Referral system is not enabled"
            }

        # Check minimum order amount
        print(f"   Checking order amount: {order_amount} >= {config.min_order_amount}")
        if order_amount < config.min_order_amount:
            return {
                'success': False,
                'message': f"Minimum order amount {config.min_order_amount} required for referral discount"
            }

        # Validate code
        is_valid, message = referral.is_code_valid()
        print("   Code Validation:", is_valid, message)
        if not is_valid:
            return {
                'success': False,
                'message': message
            }

        # Calculate discount
        discount_amount = (order_amount * config.referred_percentage) / 100
        print(f"   Calculated Discount: {order_amount} * {config.referred_percentage}% = {discount_amount}")

        # Apply discount and mark code used
        print("   Marking code as used...")
        referral.mark_code_used(discount_amount)

        # Note: We can't use self.create_reward_for_referrer here since self is the model
        # The reward creation will need to happen when the order is actually created

        print("   ✅ SUCCESS - Returning discount amount:", discount_amount)
        return {
            'success': True,
            'discount_amount': discount_amount
        }

    # Also update the mark_code_used method to not require an order
    def create_reward_for_referrer(self, referral_code, discount_amount, pos_config_id):
        """Create reward for the referrer - this will be called when order is created"""
        referral = self.env['pos.referral.code'].search([('code', '=', referral_code)], limit=1)

        if referral and not self.referral_reward_created:
            config = self.env['referral.settings'].get_settings(pos_config_id)

            if config.referred_percentage > 0:
                reward_amount = (discount_amount * config.referrer_percentage) / config.referred_percentage
                self.referral_reward_created = True
                print(f"🎁 Created reward for referrer: {reward_amount}")
                return reward_amount
        return 0


    def create_reward_for_referrer(self, referral_code, discount_amount, pos_config_id):
        """Create reward for the referrer"""
        referral = self.env['pos.referral.code'].search([('code', '=', referral_code)], limit=1)

        if referral and not self.referral_reward_created:
            config = self.env['referral.settings'].get_settings(pos_config_id)

            if config.referred_percentage > 0:
                reward_amount = (discount_amount * config.referrer_percentage) / config.referred_percentage
                self.referral_reward_created = True
                return reward_amount
        return 0

    @api.model
    def _order_fields(self, ui_order):
        """Override to include referral fields from frontend"""
        fields = super(PosOrder, self)._order_fields(ui_order)

        # Get referral data from frontend (from uiState.referralData)
        referral_data = ui_order.get('referral_data', {})

        fields.update({
            'referral_code_generated': referral_data.get('generated_code', False),
            'used_referral_code': referral_data.get('used_code', False),
            'referral_discount': referral_data.get('discount_amount', 0.0),
        })

        return fields

    def _export_for_ui(self, order):
        """Override to include referral data in receipt"""
        result = super(PosOrder, self)._export_for_ui(order)

        # Add referral information to receipt data
        receipt_referral_data = {}

        if order.referral_code_generated:
            receipt_referral_data['generated_code'] = order.referral_code_generated

        if order.used_referral_code:
            receipt_referral_data['used_code'] = order.used_referral_code
            receipt_referral_data['discount_amount'] = order.referral_discount

        # Only add to result if we have referral data
        if receipt_referral_data:
            result['receipt_referral_data'] = receipt_referral_data

        return result