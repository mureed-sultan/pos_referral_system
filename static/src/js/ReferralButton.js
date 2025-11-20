/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

// Reference Popup Component
class ReferralPopup extends Component {
    static template = "pos_referral_system.ReferralPopup";

    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.state = {
            action: "generate",
            code: "",
            error: "",
            generatedCode: "",
        };
    }

    get selectedCustomer() {
        const order = this.env.pos.get_order();
        return order ? order.get_partner() : null;
    }

    get hasPhoneNumber() {
        return this.selectedCustomer && (this.selectedCustomer.phone || this.selectedCustomer.mobile);
    }

    async generateCode() {
        const customer = this.selectedCustomer;
        if (!customer) {
            this.state.error = "Please select a customer first.";
            return;
        }

        if (!this.hasPhoneNumber) {
            this.state.error = "Customer must have a phone number to generate referral code.";
            return;
        }

        try {
            const phone = customer.phone || customer.mobile;
            const result = await this.orm.call(
                "pos.order",
                "create_referral_code",
                [customer.id, phone]
            );

            if (result) {
                const [code, referralId] = result;
                const order = this.env.pos.get_order();
                if (order) {
                    order.referral_code_generated = code;
                    order.referral_code_id = referralId;
                }
                this.state.generatedCode = code;
                this.state.error = "";
            }
        } catch (error) {
            console.error("Error generating referral code:", error);
            this.state.error = "Failed to generate referral code. Please try again.";
        }
    }

    async redeemCode() {
        if (!this.state.code.trim()) {
            this.state.error = "Please enter a referral code.";
            return;
        }

        try {
            const order = this.env.pos.get_order();
            const result = await this.orm.call(
                "pos.order",
                "list",
                [this.state.code.trim().toUpperCase(), order.get_total_with_tax()]
            );

            if (result[0]) {
                const discountAmount = result[1];
                order.referral_discount = discountAmount;
                order.used_referral_code = this.state.code.trim().toUpperCase();

                this.props.close();

                this.dialog.add("confirm", {
                    title: "Discount Applied",
                    body: `Referral discount: ${this.env.pos.format_currency(discountAmount)} applied successfully.`,
                });
            } else {
                this.state.error = result[1];
            }
        } catch (error) {
            console.error("Error applying referral code:", error);
            this.state.error = "Failed to apply referral code.";
        }
    }

    close() {
        this.props.close();
    }
}

// Simple approach: Add a global method to open referral popup
function setupReferralSystem(env) {
    env.services.dialog.addReferralPopup = function() {
        return this.add(ReferralPopup, {
            title: "Referral System",
        });
    };
}

export { ReferralPopup, setupReferralSystem };