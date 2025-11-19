/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";

// ------------------------------------------------------
// Referral Popup Component
// ------------------------------------------------------
class ReferralPopup extends Component {
    static template = "pos_referral_system.ReferralPopup";
    static props = {
        close: Function,
    };

    setup() {
        super.setup();
        this.pos = usePos();
        this.orm = useService("orm");
        this.state = useState({
            action: "generate",
            code: "",
            error: "",
            generatedCode: "",
        });
    }

    get selectedCustomer() {
        const order = this.pos.get_order();
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
                const order = this.pos.get_order();
                if (order) {
                    if (!order.referral_data) {
                        order.referral_data = {};
                    }
                    order.referral_data.generated_code = code;
                    order.referral_data.referral_id = referralId;
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
            const order = this.pos.get_order();
            const result = await this.orm.call(
                "pos.order",
                "apply_referral_discount",
                [this.state.code.trim().toUpperCase(), order.get_total_with_tax()]
            );

            if (result[0]) {
                const discountAmount = result[1];
                if (!order.referral_data) {
                    order.referral_data = {};
                }
                order.referral_data.discount_amount = discountAmount;
                order.referral_data.used_code = this.state.code.trim().toUpperCase();

                this.props.close();
                this.pos.showNotification(`Referral discount: ${this.pos.format_currency(discountAmount)} applied successfully.`);
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

// ------------------------------------------------------
// Referral Button Component
// ------------------------------------------------------
class ReferralButton extends Component {
    static template = "pos_referral_system.ReferralButton";
    static props = {}; // Add empty props definition

    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.pos = usePos();
    }

    onClick() {
        console.log("[ReferralButton] Clicked Reference Button");

        const order = this.pos.get_order();
        if (!order) {
            console.warn("[ReferralButton] No order found, cannot open popup.");
            this.pos.showNotification("Please start an order first.", { type: 'warning' });
            return;
        }

        console.log("[ReferralButton] Order found:", order);

        // Open the popup
        try {
            this.dialog.add(ReferralPopup, {
                close: () => {
                    console.log("[ReferralPopup] Close called from dialog service");
                    this.dialog.close();
                },
            });
            console.log("[ReferralButton] Dialog.add called successfully");
        } catch (error) {
            console.error("[ReferralButton] Error opening dialog:", error);
        }
    }
}

// ------------------------------------------------------
// ControlButtons Patch
// ------------------------------------------------------
patch(ControlButtons, {
    components: { ...ControlButtons.components, ReferralButton },
});

export { ReferralButton, ReferralPopup };